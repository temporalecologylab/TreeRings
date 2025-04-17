# Choose the image matching the JetPack version your code was developed on
FROM nvcr.io/nvidia/deepstream:7.0-samples-multiarch
#FROM nvcr.io/nvidia/l4t-jetpack:r36.3.0

# Install base dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    wget \
    python3-dev \
    python3-pip \
    libproj-dev \
    libsqlite3-dev \
    libcurl4-openssl-dev \
    libopenjp2-7-dev \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y \
    	gobject-introspection \
	gir1.2-gtk-3.0 \ 
	python3-gst-1.0 \
	pkg-config \
	libcairo2-dev \
    && rm -rf /var/lib/apt/lists/*
    
RUN pip3 install pyserial==3.5 \
	joblib==1.4.2 \ 
	#opencv-python==4.10.0.84 \
	pandas==1.3.5 \
	pillow==10.4.0 \
	PyGObject==3.42.1 \
	pytest==6.2.5 

# Set GDAL environment variables
ENV CPLUS_INCLUDE_PATH=/usr/local/include
ENV C_INCLUDE_PATH=/usr/local/include
#ENV LD_LIBRARY_PATH=/usr/local/lib
#ENV PATH=/usr/local/bin:$PATH
#ENV GDAL_VERSION=3.6.0

# Copy your requirements.txt (make sure it pins rasterio==1.3.10)
#COPY requirements.txt /tmp/

# Install Python dependencies
RUN apt-get update && apt-get install -y \
    	libgdal-dev \
    	gdal-bin \
    && rm -rf /var/lib/apt/lists/*
RUN pip3 install rasterio==1.3.0.post1

RUN pip3 install scikit-image \
	imutils \
	numpy==1.26.1 \
	rasterio==1.3.0.post1 \
	opencv-python \
	imagecodecs
	
RUN /opt/nvidia/deepstream/deepstream/user_additional_install.sh

RUN apt-get update && apt-get install -y \
    	x11-utils \
    	x11-apps \
    && rm -rf /var/lib/apt/lists/*

RUN ulimit -n 65535

ARG HOST_UID
ARG HOST_GID

RUN groupadd -g $HOST_GID user && \
    useradd -u $HOST_UID -g $HOST_GID -m user
    
# Install sudo to grant the user root privileges
RUN apt-get update && apt-get install -y sudo

# Grant the 'user' user root privileges without a password
RUN echo 'user ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/user

# Set the default user to 'user'

RUN mkdir /app
WORKDIR /app

ENV NVIDIA_DRIVER_CAPABILITIES $NVIDIA_DRIVER_CAPABILITIES,video
# Default command: drop into a shell for debugging

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER user
ENTRYPOINT ["./entrypoint.sh"]
CMD ["bash"]


