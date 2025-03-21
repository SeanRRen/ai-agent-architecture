Huawei Cloud EulerOS 2.0系统架构 跟CentOS类似，可使用``yum``或``dnf``安装软件包，推荐使用``dnf``。	

### Python

官方默认版本是3.9.9，如无特殊要求，可不用升级。

```shell
python -V	# Python 3.9.9
```

### Pip

```shell
# 设置 pip软件源，备用：https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
pip config set global.index-url https://repo.huaweicloud.com/repository/pypi/simple
python -m pip install --upgrade pip
```

### Conda

```shell
mkdir -p ~/miniconda3
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh -O ~/miniconda3/miniconda.sh
bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3
rm -f ~/miniconda3/miniconda.sh
source ~/miniconda3/bin/activate
conda init --all
```

### Docker & Docker Compose

​	官方默认安装的docker版本为``18.09.0``，版本比较低，很多新的特性无法使用，如docker-buildx等，建议升级到最新版本。

​	因为官方并未提供Huawei Cloud EulerOS 2.0的repo支持，所以可以采取以下方式进行安装。

1. 如果之前安装过docker，要先删掉之后再安装依赖

   ```shell
   sudo dnf remove docker docker-ce-cli docker-selinux docker-engine
   ```

2. 下载repo文件

   ```shell
   wget -O /etc/yum.repos.d/docker-ce.repo https://mirrors.huaweicloud.com/docker-ce/linux/centos/docker-ce.repo
   
   # 替换
   sudo sed -i 's+download.docker.com+mirrors.huaweicloud.com/docker-ce+' /etc/yum.repos.d/docker-ce.repo
   sudo sed -i 's+$releasever+9.9+' /etc/yum.repos.d/docker-ce.repo
   ```

3. 安装

   ```shell
   # 安装最新版本
   sudo dnf install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
   ```

4. 启动

   ```shell
   # 启动并设置开启启动
   sudo systemctl enable --now docker
   ```

5. 配置镜像加速器

   ```shell
   vi /etc/docker/daemon.json
   # 粘贴以下配置,保存退出,加速器可能会失效
   {
       "registry-mirrors": [ "https://docker.1ms.run", "https://docker.xuanyuan.me"]
   }
   ```

6. 启动

   ```shell
   # 重启
   systemctl restart docker
   ```

7. 查看docker信息

   ```shell
   docker info
   ```

### Git-LFS

git-lfs 用于git仓库中大文件下载的插件

```shell
# 有时下载速度很慢，多试几次就好了
wget https://github.com/git-lfs/git-lfs/releases/download/v3.6.1/git-lfs-linux-arm64-v3.6.1.tar.gz
tar -zxvf git-lfs-linux-arm64-v3.6.1.tar.gz
sh git-lfs-3.6.1/install.sh
git lfs install # Git LFS initialized.
```



