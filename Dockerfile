from ubuntu:focal

# tzdata is an unspecified fledge dependency
# git is because we are building from source
# nginx is for hosting the fledge-gui
# (ENV needed to get rid of the interative prompts from `apt install tzdata`)
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get -y install tzdata git nginx-light libmodbus-dev

# optionally add the repository to apt (also needed for installing new plugins within the GUI)
RUN apt-get -y install wget gnupg 
RUN wget -q -O - http://archives.fledge-iot.org/KEY.gpg | apt-key add -

# repo for ARM 32 bits
# RUN printf "\ndeb  http://archives.fledge-iot.org/latest/buster/armv7l/ /\n" >> /etc/apt/sources.list
# repo for X86_64
RUN printf "\ndeb  http://archives.fledge-iot.org/latest/ubuntu2004/x86_64/ /\n" >> /etc/apt/sources.list
# there are no prebuilt plugin fledge packages for 64 bit ARM

# building and installing fledge
RUN mkdir /root/repo
RUN cd /root/repo && git clone https://github.com/fledge-iot/fledge.git
RUN /root/repo/fledge/requirements.sh
RUN cd /root/repo/fledge && make -j16
RUN cd /root/repo/fledge && make install

# important to set this only post-install, otherwise it will assume it needs to update an existing install
ENV FLEDGE_ROOT=/usr/local/fledge

# installing and running fledge-gui, three hacks to get it running:
# 1: The requirements assumes the existence sudo, so we rewrite the script a bit
# 2: The nginx.conf is broken for newer versions of nginx because it doesn't contain an events section
# 3: Minor point but te file permissions given to the dist folder are wrong
RUN cd /root/repo && git clone https://github.com/fledge-iot/fledge-gui.git
RUN sed -i 's/sudo -E //g; s/sudo //g' /root/repo/fledge-gui/requirements && /root/repo/fledge-gui/requirements
RUN cd /root/repo/fledge-gui/ && ./build --clean-start
RUN echo "events{} $(cat /root/repo/fledge-gui/nginx.conf)" > /root/repo/fledge-gui/nginx_fixed.conf
RUN chmod ugo+x / /root /root/repo/ /root/repo/fledge-gui/ /root/repo/fledge-gui/dist/
RUN chmod -R ugo+r /root/repo/fledge-gui/dist/

# installing the libiec61850 library for good measure, as it is a non-apt-repo-available dependency of the 61850 plugin
RUN cd /root/repo && git clone https://github.com/mz-automation/libiec61850.git
RUN mkdir /root/repo/libiec61850/build
RUN cd /root/repo/libiec61850/build && cmake .. && make && make install
ENV LIB_61850=/root/repo/libiec61850

# modified modbus plugin that support Janitza's
RUN cd /root/repo && git clone https://github.com/alliander-opensource/fledge-south-modbus-c
RUN cd /root/repo/fledge-south-modbus-c && mkdir build
RUN cd /root/repo/fledge-south-modbus-c/build && cmake -DFLEDGE_SRC=/root/repo/fledge .. && make

# you might want to install some plugins by default, you can install more in GUI
# RUN apt-get -y install fledge-south-modbus fledge-south-benchmark fledge-rule-average
###
COPY sinusoid /usr/local/fledge/python/fledge/plugins/south/sinusoid
COPY  ema /usr/local/fledge/python/fledge/plugins/filter/ema
COPY  wma_filter /usr/local/fledge/python/fledge/plugins/filter/wma_filter
RUN python3 -m pip install numpy
###
# 8081 is the Fledge REST API HTTP port
# 1995 is the Fledge REST API HTTPS port
# 502 is the default Modbus-TCP port, useful for testing
# 80 is for the Fledge GUI web interface
EXPOSE 8081 1995 502 80

CMD bash /usr/local/fledge/bin/fledge start && nginx -c /root/repo/fledge-gui/nginx_fixed.conf -p /root/repo/fledge-gui && bash

LABEL maintainer="bob.lucassen@alliander.com" \
      vendor="Alliander" \
      author="Bob Lucassen" \
      version="1.0.0" \
      description="A minimal fledge instance"
