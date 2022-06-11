# NOTE: Use the run-container.sh script to build and launch this container.

# NOTE: Multi-stage builds require Docker >= 17.05.
FROM rockylinux:8.5 AS base

# update packages and install requirements
RUN dnf -y upgrade-minimal && \
    dnf install -y python39

# NOTE: We don't need the following stuff for the build step, but it's nice to not have to re-install
# it all every time we change the requirements :-/

# install Java
ARG JAVA_URL=https://download.oracle.com/java/17/archive/jdk-17.0.2_linux-x64_bin.tar.gz
RUN curl -s "$JAVA_URL" | tar -xz -C /usr/bin/

# install Firefox
ARG FIREFOX_URL=https://ftp.mozilla.org/pub/firefox/releases/94.0.2/linux-x86_64/en-US/firefox-94.0.2.tar.bz2
RUN dnf install -y bzip2 xorg-x11-server-Xvfb gtk3 dbus-glib && \
    curl -s "$FIREFOX_URL" | tar -jx -C /usr/local/ && \
    ln -s /usr/local/firefox/firefox /usr/bin/firefox && \
    echo "exclude=firefox" >>/etc/dnf/dnf.conf

# install geckodriver
ARG GECKODRIVER_URL=https://github.com/mozilla/geckodriver/releases/download/v0.31.0/geckodriver-v0.31.0-linux64.tar.gz
RUN curl -sL "$GECKODRIVER_URL" | tar -xz -C /usr/bin/

# clean up
RUN dnf clean all

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

FROM base AS build

# set up a virtualenv
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip

# install the application requirements
COPY requirements.txt requirements-dev.txt /tmp/
RUN pip3 install -r /tmp/requirements.txt
ARG CONTROL_TESTS_PORT
RUN if [ -n "$CONTROL_TESTS_PORT" ]; then \
    pip3 install -r /tmp/requirements-dev.txt \
; fi

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

FROM base

# copy the virtualenv from the build image
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

# FUDGE! We need this to stop spurious warning messages:
#   Fork support is only compatible with the epoll1 and poll polling strategies
# Setting the verbosity to ERROR should suppress these, but doesn't :-/
#   https://github.com/grpc/grpc/issues/17253
#   https://github.com/grpc/grpc/blob/master/doc/environment_variables.md
ENV GRPC_VERBOSITY=NONE

# run the application
EXPOSE 5010
COPY docker/run.sh ./
CMD ./run.sh
