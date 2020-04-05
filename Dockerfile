# NOTE: Use the run-container.sh script to build and launch this container.

# We do a multi-stage build (requires Docker >= 17.05) to install everything, then copy it all
# to the final target image.

FROM centos:8 AS base

# update packages and install Python
RUN dnf -y upgrade-minimal && \
    dnf install -y python36 && \
    dnf clean all

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

FROM base AS build

# set up a virtualenv
RUN python3.6 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip

# install the application requirements
COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements.txt
ARG ENABLE_TESTS
RUN if [ "$ENABLE_TESTS" ]; then pip install -r requirements-dev.txt ; fi

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

FROM base

# copy the virtualenv from the build image
COPY --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# install the application
WORKDIR /app
COPY vasl_templates vasl_templates
COPY setup.py requirements.txt requirements-dev.txt LICENSE.txt ./
RUN pip install -e .

# copy the config files
COPY docker/config/* vasl_templates/webapp/config/
ARG ENABLE_TESTS
RUN if [ "$ENABLE_TESTS" ]; then echo "ENABLE_REMOTE_TEST_CONTROL = 1" >>vasl_templates/webapp/config/debug.cfg ; fi

# create a new user
RUN useradd --create-home app
USER app

EXPOSE 5010
COPY docker/run.sh .
CMD ./run.sh
