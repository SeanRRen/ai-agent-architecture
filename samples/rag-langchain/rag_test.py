from langchain_community.document_loaders import (
    PDFPlumberLoader,
    TextLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredPowerPointLoader,
    UnstructuredExcelLoader,
    CSVLoader,
    UnstructuredMarkdownLoader,
    UnstructuredXMLLoader,
    UnstructuredHTMLLoader,
) # 从 langchain_community.document_loaders 模块中导入各种文档加载器类
from langchain.text_splitter import (
    CharacterTextSplitter,
    RecursiveCharacterTextSplitter,
    MarkdownTextSplitter,
    PythonCodeTextSplitter,
    LatexTextSplitter,
    SpacyTextSplitter,
    NLTKTextSplitter
) # 从 langchain.text_splitter 模块中导入各种文档分块类
from langchain_text_splitters import RecursiveCharacterTextSplitter # 文档拆分chunk
from sentence_transformers import SentenceTransformer # 加载和使用Embedding模型
import faiss # Faiss向量库 faiss-cpu
import numpy as np # 处理嵌入向量数据，用于Faiss向量检索
from dashscope import Generation #调用Qwen大模型
from http import HTTPStatus #检查与Qwen模型HTTP请求状态
import sys,os,uuid,shutil
import dashscope
from FlagEmbedding import FlagReranker
from rank_bm25 import BM25Okapi
import jieba
import chromadb
os.environ["TOKENIZERS_PARALLELISM"] = "false" # 不使用分词并行化操作, 避免多线程或多进程环境中运行多个模型引发冲突或死锁
# 设置Qwen系列具体模型及对应的调用API密钥，从阿里云百炼大模型服务平台获得
qwen_model = "qwen-turbo"
qwen_api_key = "sk-5aacfba9df56416d879888908fc1b2b4"

# 定义文档解析加载器字典，根据文档类型选择对应的文档解析加载器类和输入参数
DOCUMENT_LOADER_MAPPING = {
    ".pdf": (PDFPlumberLoader, {}),
    ".txt": (TextLoader, {"encoding": "utf8"}),
    ".doc": (UnstructuredWordDocumentLoader, {}),
    ".docx": (UnstructuredWordDocumentLoader, {}),
    ".ppt": (UnstructuredPowerPointLoader, {}),
    ".pptx": (UnstructuredPowerPointLoader, {}),
    ".xlsx": (UnstructuredExcelLoader, {}),
    ".csv": (CSVLoader, {}),
    ".md": (UnstructuredMarkdownLoader, {}),
    ".xml": (UnstructuredXMLLoader, {}),
    ".html": (UnstructuredHTMLLoader, {}),
}
def load_document(file_path):
    """
    解析多种文档格式的文件，返回文档内容字符串
    """
    ext = os.path.splitext(file_path)[1]  # 获取文件扩展名，确定文档类型
    loader_tuple = DOCUMENT_LOADER_MAPPING.get(ext)  # 获取文档对应的文档解析加载器类和参数元组
    if loader_tuple is None: # 判断文档格式是否在加载器支持范围
        print(file_path+f"，不支持的文档类型: '{ext}'")
        return ""

    loader_class, loader_args = loader_tuple # 解包元组，获取文档解析加载器类和参数
    loader = loader_class(file_path, **loader_args)  # 创建文档解析加载器实例，并传入文档文件路径
    documents = loader.load()  # 加载文档
    content = "\n".join([doc.page_content for doc in documents])  # 多页文档内容组合为字符串
    print(f"文档 {file_path} 的部分内容为: {content[:100]}...")  # 仅用来展示文档内容的前100个字符
    return content

def split_text(folder_path):
    """
    加载文件夹中的所有文档文件，并将其内容分割成文档块，
    """
    # 初始化空的chunks列表，用于存储所有文档文件的文本块
    all_chunks = []
    all_ids = []
    # 遍历文件夹中的所有文档文件
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)

        # 检查是否为文件
        if os.path.isfile(file_path):
            # 解析文档文件，获得文档字符串内容
            document_text = load_document(file_path)
            print(f"文档 {file_name} 的总字符数: {len(document_text)}")
            # # 可以更换为CharacterTextSplitter、MarkdownTextSplitter、PythonCodeTextSplitter、LatexTextSplitter、NLTKTextSplitter等
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
            # 将文档文本分割成文本块Chunk
            chunks = text_splitter.split_text(document_text)
            print(f"分割的文本Chunk数量: {len(chunks)}") 
            all_chunks.extend(chunks)
            all_ids.extend([str(uuid.uuid4()) for _ in range(len(chunks))])
    return all_ids,all_chunks

def load_embedding_model():
    print("开始加载Embedding模型...")
    # SentenceTransformer读取绝对路径下的bge-small-zh-v1.5模型，非下载
    embedding_model = SentenceTransformer('bge-small-zh-v1.5')
    print(f"模型最大输入长度: {embedding_model.max_seq_length}") 
    return embedding_model

def indexing_process(folder_path,embedding_model,collection):
    """
    索引流程：加载文件夹中的所有文档文件，并将其内容分割成文档块，计算这些小块的嵌入向量并将其存储在Faiss向量数据库中。
    """
    print("开始索引流程...")
    all_ids,all_chunks = split_text(folder_path)

    if len(all_chunks) == 0:
        print("未找到文本块Chunk，文档可能不支持解析")
        return
    
    # 文本块转化为嵌入向量列表，normalize_embeddings表示对嵌入向量进行归一化，用于准确计算相似度
    embeddings = [embedding_model.encode(chunk, normalize_embeddings=True).tolist() for chunk in all_chunks]
    print("文本块Chunk转化为嵌入向量完成...")
    collection.add(ids=all_ids, embeddings=embeddings, documents=all_chunks)
    print("嵌入生成完成，向量数据库存储完成.")
    print("索引过程完成...")

def rerank(query, chunks, top_k=3):
    """
    rerank流程：检索到的文本块进行重新排序，并返回最相关的文本块。
    """
    print("开始rerank流程...")
    # 初始化重排序模型，使用BAAI/bge-reranker-v2-m3
    reranker = FlagReranker('BAAI/bge-reranker-v2-m3', use_fp16=True)
    # 构造输入对，每个 query 与 chunk 形成一对
    input_pairs = [[query, chunk] for chunk in chunks]
    # 计算每个 chunk 与 query 的语义相似性得分
    scores = reranker.compute_score(input_pairs, normalize=True)
    print("文档块重排序得分:", scores)
     # 对得分进行排序并获取排名前 top_k 的 chunks
    sorted_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    reranking_chunks = [chunks[i] for i in sorted_indices[:top_k]]
    # 打印前三个 score 对应的文档块
    for i in range(top_k):
        print(f"重排序文档块{i+1}: 相似度得分：{scores[sorted_indices[i]]}，文档块信息：{reranking_chunks[i]}\n")
    return reranking_chunks

def retrieval_process(query, collection, embedding_model, top_k=3):
    """
    检索流程：将用户查询Query转化为嵌入向量，并在Faiss索引中检索最相似的前k个文本块。
    """
    print(f"查询语句: {query}")
    # 将查询转化为嵌入向量，从向量库中检索最相似的前k个文本块。
    query_embedding = embedding_model.encode(query, normalize_embeddings=True).tolist()
    vector_results = collection.query(query_embeddings=[query_embedding], n_results=top_k)
    vector_chunks = []
    print(f"向量检索最相似的前 {top_k} 个文本块:")
    for rank,(doc_id,doc) in enumerate(zip(vector_results['ids'][0], vector_results['documents'][0])):
        print(f"向量检索排名: {rank + 1},文本块ID: {doc_id},文本块信息:\n{doc}\n")
        vector_chunks.append(doc)
    
    # 使用 jieba.cut 对查询文本进行分词，生成分词列表
    tokenized_query = list(jieba.cut(query))
    all_docs = collection.get()['documents']
    # 对每篇文档进行分词，生成分词后的语料库
    tokenized_corpus = [list(jieba.cut(doc)) for doc in all_docs]
    # 基于分词后的语料库计算查询与文档的相似度得分
    bm25 = BM25Okapi(tokenized_corpus)
    bm25_scores = bm25.get_scores(tokenized_query)
    # 根据相似度得分排序，选取前 top_k 个文档索引
    bm25_top_k_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:top_k]
    bm25_chunks = [all_docs[i] for i in bm25_top_k_indices]
    print(f"BM25 检索最相似的前 {top_k} 个文本块:\n{bm25_chunks}")
    
    # 使用重排序模型对检索结果进行重新排序，输出重排序后的前top_k文档块
    # reranking_chunks = rerank(query,vector_chunks + bm25_chunks, top_k)
    print("检索过程完成...")
    return vector_chunks

def generate_process(query, chunks):
    """
    生成流程：调用Qwen大模型云端API，根据查询和文本块生成最终回复。
    """
    llm_model = qwen_model
    dashscope.api_key = qwen_api_key

    # 构建参考文档内容，格式为“参考文档1: \n 参考文档2: \n ...”等
    context = "\n".join([f"参考文档{i+1}: \n {chunk}\n" for i, chunk in enumerate(chunks)])
    # 构建生成模型所需的Prompt，包含用户查询和检索到的上下文
    prompt = f"根据以下参考文档回答问题，回答一定要忠于原文，简洁但不丢信息，不要胡乱编造。\n问题：{query}\n\n{context}"
    print(f"生成模型的Prompt: {prompt}")
    # 准备请求消息，将prompt作为输入
    messages = [{'role': 'user', 'content': prompt}]
    try:
        # 调用Qwen大模型云端API，生成回复
        responses = Generation.call(
            model=llm_model,
            messages=messages,
            result_format='message', # 设置输出为'message'格式
            stream=True,  # 设置输出方式为流式输出
            incremental_output=True  # 增量式流式输出
        )
        print("生成过程开始")
        # 逐步获取和处理模型的增量输出
        for response in responses:
            if response.status_code == HTTPStatus.OK:
                print(response.output.choices[0]['message']['content'], end='')
            else:
                print(f"请求失败: {response.status_code} - {response.message}")
        print("\n生成过程完成...")
    except Exception as e:
        print(f"大模型生成过程中发生错误: {e}")
def main():
    print("RAG 流程开始...")

    # 创建向量数据库文件
    chroma_db_path = os.path.abspath("chroma_db")
    if os.path.exists(chroma_db_path):
        shutil.rmtree(chroma_db_path)

    # 创建向量数据库客户端及索引集合
    client = chromadb.PersistentClient(path=os.path.abspath(chroma_db_path))
    collection = client.get_or_create_collection(name="documents") 

    #  加载embedding模型
    embedding_model = load_embedding_model()

    # 索引流程：加载PDF文件，分割文本块，计算嵌入向量，存储在向量数据库中
    indexing_process('data', embedding_model,collection)

    query="公民是否拥有房产的所有权力？"
    # 检索流程：将用户查询转化为嵌入向量，检索最相似的文本块
    retrieval_chunks = retrieval_process(query, collection, embedding_model)

    # 生成流程：调用Qwen大模型生成响应
    generate_process(query, retrieval_chunks)

    print("RAG 流程结束...")


if __name__ == '__main__':
    main()

