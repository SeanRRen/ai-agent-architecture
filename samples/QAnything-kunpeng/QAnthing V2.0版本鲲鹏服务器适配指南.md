下面介绍如何快速在鲲鹏云服务器纯CPU部署QAnything项目

#### 购买弹性云服务器

| 配置项目         | 项目内容                                    |
| ---------------- | ------------------------------------------- |
| **实例规格**     | 鲲鹏内存优化型\|km1.xlarge.8\|4vCPUs\|32GiB |
| **操作系统镜像** | Huawei Cloud EulerOS 2.0 标准版 64位 ARM版  |
| **存储**         | 系统盘：超高IO，100GiB                      |

#### 基础环境

请看``如何快速搭建项目环境.md``

#### 下载项目

```shell
git clone https://github.com/netease-youdao/QAnything.git
```

#### 启动项目

```shell
cd QAnything
docker compose -f docker-compose-linux.yaml up
# 当日志输出"qanything后端服务已就绪!"后，启动完毕！
```

#### 体验项目

```shell
http://localhost:8777/qanything/
```

#### 关闭服务

```shell
# 前台启动服务方式如下：
docker compose -f docker-compose-xxx.yaml up 
# 关闭服务请按Ctrl+C

# 后台启动服务方式如下：
docker compose -f docker-compose-xxx.yaml up -d  
# 关闭服务请执行以下命令
docker compose -f docker-compose-xxx.yaml down
```

#### 日志查看

查看服务启动相关日志，请查看`QAnything/logs/debug_logs`目录下的日志文件

- **debug.log**：用户请求处理日志
- **main_server.log**：后端服务运行日志
- **rerank_server.log**：rerank服务运行日志
- **ocr_server.log**：OCR服务运行日志
- **embedding_server.log**：向量化服务运行日志
- **rerank_server.log**：检索增强服务运行日志
- **insert_files_server.log**：文件上传服务运行日志
- **pdf_parser_server.log**：pdf解析服务运行日志

详细上传文件日志请查看`QAnything/logs/insert_logs`目录下的日志文件。

详细问答日志请查看`QAnything/logs/qa_logs`目录下的日志文件。

详细embedding日志请查看`QAnything/logs/embed_logs`目录下的日志文件。

详细rerank日志请查看`QAnything/logs/rerank_logs`目录下的日志文件。

#### 启动失败

等了半天还是访问不了，日志显示如下：

![局部截取_20250320_174156](.\assets\局部截取_20250320_174156.png)

通过``docker ps -a``看到``qanything-container-local``容器状态显示为``Exited (255)``

![局部截取_20250320_174108](.\assets\局部截取_20250320_174108.png)

**问题现象：exec /bin/bash: exec format error**

**问题原因**：docker镜像是基于X86架构下构建的无法在ARM架构下运行，需要在ARM架构下重新构建。

#### 在ARM架构下构建QAnything镜像

1. 进入``build_images``，查看``Dockerfile``，可以得到以下几点信息

   - ``Dockerfile``文件要移动到父目录下才能构建
   - 需要准备``models、nltk_data``文件夹数据

   ```shell
   # 复制 requirements.txt 文件到容器中
   COPY requirements.txt /tmp/requirements.txt
   
   # 复制 models 文件夹到 /root 目录
   COPY models /root/models
   COPY nltk_data /root/nltk_data
   ```

   要知道``model``文件夹下要准备什么数据就要看，这个文件复制到容器后是如何使用的，通过``docker-compose-linux.yaml`` 可知运行``qanything-container-local``容器时会执行``/bin/bash -c "cd /workspace/QAnything && bash scripts/entrypoint.sh"``，于是看``script/entrypoint.sh``中提供了哪些信息。

   跟``/root/models``和``/root/nltk_data``有关的信息如下：

   ```shell
   # 创建软连接
   if [ ! -L "/workspace/QAnything/qanything_kernel/dependent_server/embedding_server/embedding_model_configs_v0.0.1" ]; then  # 如果不存在软连接
     cd /workspace/QAnything/qanything_kernel/dependent_server/embedding_server && ln -s /root/models/linux_onnx/embedding_model_configs_v0.0.1 .
   fi
   
   if [ ! -L "/workspace/QAnything/qanything_kernel/dependent_server/rerank_server/rerank_model_configs_v0.0.1" ]; then  # 如果不存在软连接
     cd /workspace/QAnything/qanything_kernel/dependent_server/rerank_server && ln -s /root/models/linux_onnx/rerank_model_configs_v0.0.1 .
   fi
   
   if [ ! -L "/workspace/QAnything/qanything_kernel/dependent_server/ocr_server/ocr_models" ]; then  # 如果不存在软连接
     cd /workspace/QAnything/qanything_kernel/dependent_server/ocr_server && ln -s /root/models/ocr_models .  # 创建软连接
   fi
   
   if [ ! -L "/workspace/QAnything/qanything_kernel/dependent_server/pdf_parser_server/pdf_to_markdown/checkpoints" ]; then  # 如果不存在软连接
     cd /workspace/QAnything/qanything_kernel/dependent_server/pdf_parser_server/pdf_to_markdown/ && ln -s /root/models/pdf_models checkpoints  # 创建软连接
   fi
   
   if [ ! -L "/workspace/QAnything/nltk_data" ]; then  # 如果不存在软连接
     cd /workspace/QAnything/ && ln -s /root/nltk_data .  # 创建软连接
   fi
   ```

   从脚本内容结合官方README可知，models文件夹中要准备``embedding``、``rerank``、``ocr``、``pdf``四个模型，``nltk_data``下要准备``nltk`` 数据

2. ``model``文件夹下要准备的数据

   1. 安装``modelscope``

      ```shell
      pip install modelscope
      ```

   2. ``bce-embedding-base_v1``

      ```shell
      # 在QAnything目录下执行
      modelscope download --model netease-youdao/bce-embedding-base_v1 --local_dir ./models/linux_onnx/embedding_model_configs_v0.0.1
      ```

   3. ``bce-reranker-base_v1``

      ```shell
      # 在QAnything目录下执行
      modelscope download --model netease-youdao/bce-reranker-base_v1 --local_dir ./models/linux_onnx/rerank_model_configs_v0.0.1
      ```

   4. ``pdf_models``和``ocr_model``

      ```shell
      modelscope download --model netease-youdao/QAnything-pdf-parser --local_dir ./models/pdf_models
      ```

      pdf_models中已经包含了ocr，可以重用，这里要改下``entrypoint.sh``中ocr_models路径

      ```shell
      if [ ! -L "/workspace/QAnything/qanything_kernel/dependent_server/ocr_server/ocr_models" ]; then  # 如果不存在软连接
        cd /workspace/QAnything/qanything_kernel/dependent_server/ocr_server && ln -s /root/models/pdf_models/ocr ocr_models  # 创建软连接
      fi
      ```

      至此models中的数据准备完成。

3. ``nltk_data``文件夹下要准备的数据

   ```shell
   modelscope download --dataset CaiJichang/nltk_data --local_dir ./nltk_data
   ```

   至此nltk_data中的数据准备完成。

4. 构建docker镜像

   构建之前需要对Dockfile做一些优化，加快构建速度。在``QAnything``# 在目录下执行重新创建新的``Dockerfile``

   ```shell
   vi Dockerfile
   # 添加以下内容
   
   # 使用官方 Python 3.10.14 镜像作为基础镜像
   FROM python:3.10-slim
   
   # 替换APT源
   RUN sed -i.bak 's/http:\/\/deb.debian.org\//https:\/\/mirrors.tuna.tsinghua.edu.cn\//g' /etc/apt/sources.list.d/debian.sources \
      && rm -f /etc/apt/sources.list.d/debian.sources.bak
   # 设置时区
   ENV TZ=Asia/Shanghai
   RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
   
   # 安装 vim
   RUN apt-get update && apt-get install -y \
       vim \
       wget \
       htop \
       build-essential \
       procps \
       && rm -rf /var/lib/apt/lists/*
   
   # 创建TikToken缓存目录
   RUN mkdir /opt/tiktoken_cache
   
   # 下载TikToken模型缓存
   ARG TIKTOKEN_URL="https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken"
   RUN wget -O /opt/tiktoken_cache/$(echo -n $TIKTOKEN_URL | sha1sum | head -c 40) "$TIKTOKEN_URL"
   
   # 设置环境变量指向TikToken缓存目录
   ENV TIKTOKEN_CACHE_DIR=/opt/tiktoken_cache
   
   # 复制 requirements.txt 文件到容器中
   COPY requirements.txt /tmp/requirements.txt
   
   # 安装 Python 依赖(torch单独安装CPU版本)
   RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
   RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r /tmp/requirements.txt
   
   # 复制 models 文件夹到 /root 目录
   COPY models /root/models
   COPY nltk_data /root/nltk_data
   
   # 设置工作目录
   WORKDIR /workspace
   
   # 清理 APT 缓存
   RUN apt-get clean && rm -rf /var/lib/apt/lists/*
   
   # 设置默认命令
   CMD ["/bin/bash"]
   ```

   同时对``requirements.txt``也要做些优化，建议先备份原文件

   ```shell
   mv requirements.txt requirements.txt.bak
   vi requirements.txt
   # 添加以下内容
   onnxruntime==1.17.1
   xgboost-cpu==3.0.0
   concurrent-log-handler==0.9.25
   boto3==1.34.79
   sanic==23.6.0
   sanic_ext==23.6.0
   langchain-openai==0.3.7
   langchain_elasticsearch==0.3.2
   langchain-community==0.3.18
   unstructured==0.12.4
   unstructured[pptx]==0.12.4
   unstructured[md]==0.12.4
   opencv-python-headless==4.9.0.80
   python-dotenv==1.0.1
   mysql-connector-python==8.2.0
   pymilvus==2.5.5
   aiomysql==0.2.0
   PyMuPDF==1.24.4
   openpyxl==3.1.2
   python-docx==1.1.0
   newspaper4k==0.9.3.1
   newspaper4k[zh]
   duckduckgo-search==5.3.0b4
   html2text==2024.2.26
   mistune==3.0.2
   flair==0.13.0
   nltk==3.8.1
   pandas==2.1.1
   scikit-learn==1.3.2
   chardet==5.2.0
   scipy==1.10.1
   fastchat==0.1.0
   wikipedia==1.4.0
   Wikipedia-API==0.6.0
   rouge-score==0.1.2
   toml==0.10.2
   tqdm==4.66.1
   anthropic==0.25.7
   streamlit==1.34.0
   zhipuai==2.0.1.20240429
   tiktoken==0.7.0
   modelscope==1.13.0
   cryptography==42.0.8
   shapely==2.0.4
   pyclipper==1.3.0.post5
   pdfplumber==0.11.0
   markdownify==0.12.1
   datrie==0.8.2
   hanziconv==0.3.2
   PyPDF2==3.0.1
   lxml_html_clean==0.1.1
   docx2txt==0.8
   ```

   下面开始构建

   ```shell
   # 在QAnything目录下执行
   docker build -t xixihahaliu01/qanything-linux:v1.5.1 .
   ```

   

5. 



