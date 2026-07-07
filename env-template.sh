# 此脚本用于创建CANN生态的容器，用于模型推理、算子开发等

# 设定容器的名字

export NAME=你的容器名字

# 设置待使用的镜像
# 自定义配置镜像方法：
# 1. 访问quay.io/ascend/vllm-ascend（或者quay.io/ascend/cann）查看镜像资源，根据操作系统（ubuntu/openEuler），服务器型号（A2-910B服务器，A3-910C服务器）,CANN版本等选择镜像
# 2. 拉取镜像时候，用 quay.io/ascend/cann:镜像的tag号 来索引。例如，quay.io/ascend/vllm-ascend:main-openeuler
export IMAGE=quay.io/ascend/cann:9.0.0-a3-openeuler24.03-py3.12-devel


# 把工作目录绑定到容易内
export HOST_MODEL_DIR=你的工作目录路径 # 这里输入你的工作目录路径
export CONTAINER_MODEL_DIR=/root+你的工作目录路径   # 这里输入容器内的目标路径

# 通过 --device /dev/davinciN 的编号指定绑定哪张NPU到容器；
# 绑定多卡就多加几条 --device /dev/davinciN（例如再加一行：  --device /dev/davinci1 \）。
docker run -d \
  --name ${NAME} \
  --restart unless-stopped \
  --privileged \
  --network host \
  --shm-size 16g \
  --device /dev/davinci0 \
  --device /dev/davinci_manager \
  --device /dev/devmm_svm \
  --device /dev/hisi_hdc \
  -v /usr/local/dcmi:/usr/local/dcmi \
  -v /usr/local/bin/npu-smi:/usr/local/bin/npu-smi \
  -v /usr/local/Ascend/driver:/usr/local/Ascend/driver \
  -v /etc/ascend_install.info:/etc/ascend_install.info:ro \
  -v ${HOST_MODEL_DIR}:${CONTAINER_MODEL_DIR} \
  ${IMAGE} \
  bash -c "while true; do sleep 3600; done"
