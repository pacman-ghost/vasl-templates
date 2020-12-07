# NOTE: Use the run-container.sh script to build and launch this container.

# We do a multi-stage build (requires Docker >= 17.05) to install everything, then copy it all
# to the final target image.

FROM centos:8 AS base

# update packages
RUN dnf -y upgrade-minimal

# install Python
RUN dnf install -y python36 && pip3 install --upgrade pip

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

# NOTE: We install the Python dependencies into a temporary intermediate stage, then copy everything over
# to the final image, because some modules (e.g. grpcio) need pre-requisites to be installed.
# This saves us about 300 MB for the final image and, importantly, adding a requirement doesn't cause us
# to re-install Java and Firefox below, when we start building the final image.

FROM base AS build

# set up a virtualenv
RUN python3 -m venv /opt/venv && pip3 install --upgrade pip
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
COPY docker/config/ ./vasl_templates/webapp/config/

# create a new user
RUN useradd --create-home app
USER app

EXPOSE 5010
COPY docker/run.sh ./
CMD ./run.sh
