FROM ubuntu:22.04 AS build

ARG CONDA_DIR=/opt/conda
ARG ENV_DIR=/venv

# Instal basic utilities
RUN apt-get update && \
    apt-get install -y --no-install-recommends git wget unzip bzip2 sudo build-essential ca-certificates libc6-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install miniconda
ENV PATH=$CONDA_DIR/bin:$PATH
RUN wget -q  https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh -O /tmp/miniforge.sh && \
    echo "export PATH=$CONDA_DIR/bin:PATH" > /etc/profile.d/conda.sh && \
    /bin/bash /tmp/miniforge.sh -b -p $CONDA_DIR && \
    rm -rf /tmp/*


# 根据架构选择正确的 Miniforge 安装程序
# RUN if [ "$TARGETARCH" = "arm64" ]; then \
#         wget -q https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-aarch64.sh -O /tmp/miniforge.sh; \
#     else \
#         wget -q https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh -O /tmp/miniforge.sh; \
#     fi && \
#     echo "export PATH=$CONDA_DIR/bin:PATH" > /etc/profile.d/conda.sh && \
#     /bin/bash /tmp/miniforge.sh -b -p $CONDA_DIR && \
#     rm -rf /tmp/*

WORKDIR /root

# Install packages
ADD ./environment_cloud_run.yml .
RUN mamba env create --name tmp --file ./environment_cloud_run.yml && \
    mamba install -y -c conda-forge conda-pack && \
    conda clean -tipy

# Run conda-pack
RUN mkdir -p $ENV_DIR
RUN conda-pack -n tmp -o /tmp/env.tar && \
    tar xf /tmp/env.tar -C $ENV_DIR && \
    rm /tmp/env.tar
RUN $ENV_DIR/bin/conda-unpack


# Runtime image
FROM ubuntu:22.04

ARG ENV_DIR=/venv
ARG USERNAME=docker
ARG USERID=1000

# Instal basic utilities
RUN apt-get update && \
    apt-get install -y --no-install-recommends apt-transport-https \
    ca-certificates curl gnupg git wget unzip bzip2 sudo p7zip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create the user
RUN useradd --create-home -s /bin/bash --no-user-group -u $USERID $USERNAME && \
    adduser $USERNAME sudo && \
    echo "$USERNAME ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

ENV PATH=$ENV_DIR/bin:$PATH
RUN mkdir -p $ENV_DIR && chown -R $USERNAME $ENV_DIR
COPY --chown=1000 --from=build $ENV_DIR $ENV_DIR

USER $USERNAME
WORKDIR /home/$USERNAME

COPY --chown=1000 api_service api_service
COPY --chown=1000 start_server.sh start_server.sh

ENV PORT=8000
CMD ["bash", "start_server.sh"]
