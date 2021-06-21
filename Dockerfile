# NOTE: Use the run-container.sh script to build and launch this container.

# We do a multi-stage build (requires Docker >= 17.05) to install everything, then copy it all
# to the final target image.

FROM centos:8 AS base

# update packages
RUN dnf -y upgrade-minimal

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

# NOTE: We install the Python dependencies into a temporary intermediate stage, then copy everything over
# to the final image, because some modules (e.g. grpcio) need pre-requisites to be installed.
# This saves us about 300 MB for the final image and, importantly, adding a requirement doesn't cause us
# to re-install Java and Firefox below, when we start building the final image.

FROM base AS build

# install Python
# NOTE: The version of Python we want is newer than what's in Centos 8,
# so we have to install from source :-/
RUN dnf -y groupinstall "Development Tools" && \
    dnf -y install openssl-devel bzip2-devel libffi-devel sqlite-devel
RUN cd /tmp && \
    dnf -y install wget && \
    wget https://www.python.org/ftp/python/3.8.7/Python-3.8.7.tgz && \
    tar xvf Python-3.8.7.tgz && \
    cd Python-3.8.7/ && \
    ./configure --enable-optimizations && \
    make install

# set up a virtualenv
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# install the application requirements
COPY requirements.txt requirements-dev.txt ./
RUN pip3 install -r requirements.txt
ARG CONTROL_TESTS_PORT
RUN if [ -n "$CONTROL_TESTS_PORT" ]; then \
    dnf install -y gcc-c++ python3-devel && \
    pip3 install -r requirements-dev.txt \
; fi

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

FROM base

# copy the Python installation from the build image
COPY --from=build /usr/local/bin/python3.8 /usr/local/bin/python3.8
COPY --from=build /usr/local/lib/python3.8 /usr/local/lib/python3.8
COPY --from=build /usr/local/bin/pip3 /usr/local/bin/pip3
RUN ln -s /usr/local/bin/python3.8 /usr/local/bin/python3

# install Java
RUN url="https://download.java.net/java/GA/jdk15.0.1/51f4f36ad4ef43e39d0dfdbaf6549e32/9/GPL/openjdk-15.0.1_linux-x64_bin.tar.gz" ; \
    curl -s "$url" | tar -C /usr/bin/ -xz

# install Firefox
RUN dnf install -y wget bzip2 xorg-x11-server-Xvfb gtk3 dbus-glib && \
    wget -qO- "https://download.mozilla.org/?product=firefox-latest-ssl&os=linux64&lang=en-US" \
        | tar -C /usr/local/ -jx && \
    ln -s /usr/local/firefox/firefox /usr/bin/firefox && \
    echo "exclude=firefox" >>/etc/dnf/dnf.conf

# install geckodriver
RUN url=$( curl -s https://api.github.com/repos/mozilla/geckodriver/releases/latest | grep -Poh 'https.*linux64\.tar\.gz(?!\.)' ) && \
    curl -sL "$url" | tar -C /usr/bin/ -xz

# clean up
RUN dnf clean all

# install the application requirements
COPY --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# install the application
WORKDIR /app
COPY vasl_templates/ ./vasl_templates/
COPY vassal-shim/release/vassal-shim.jar ./vassal-shim/release/
COPY setup.py requirements.txt requirements-dev.txt LICENSE.txt ./
RUN pip3 install --editable .

# install the config files
COPY vasl_templates/webapp/config/logging.yaml.example ./vasl_templates/webapp/config/logging.yaml
COPY docker/config/ ./vasl_templates/webapp/config/

# create a new user
# NOTE: It would be nice to just specify the UID/GID in the "docker run" command, but VASSAL has problems
# if there is no user :-/ We could specify these here, but that would bake them into the image.
# In general, this is not a problem, since the application doesn't need to access files outside the container,
# but if the user wants to e.g. keep the cached scenario index files outside the container, and they are
# running with a non-default UID/GID, they will have to manage permissions themselves. Sigh...
RUN useradd --create-home app
USER app

# run the application
EXPOSE 5010
COPY docker/run.sh ./
CMD ./run.sh
