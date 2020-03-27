# NOTE: Use the run-container.sh script to build and launch this container.

# We do a multi-stage build (requires Docker >= 17.05) to install everything, then copy it all
# to the final target image.

FROM python:alpine3.6 AS base

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

FROM base AS build

# install the requirements
# NOTE: pillow needs zlib and jpeg, lxml needs libxslt, we need build-base for gcc, etc.
RUN apk add --no-cache build-base zlib-dev jpeg-dev libxslt-dev

# install the application requirements
COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements.txt
ARG ENABLE_TESTS
RUN if [ "$ENABLE_TESTS" ]; then pip install -r requirements-dev.txt ; fi

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

FROM base
COPY --from=build /usr/local/lib/python3.6/site-packages /usr/local/lib/python3.6/site-packages
RUN apk add --no-cache libjpeg

# install the application
WORKDIR /app
COPY vasl_templates vasl_templates
COPY setup.py requirements.txt requirements-dev.txt LICENSE.txt ./
RUN pip install -e .

# copy the config files
COPY docker/config/* vasl_templates/webapp/config/
ARG ENABLE_TESTS
RUN if [ "$ENABLE_TESTS" ]; then echo "ENABLE_REMOTE_TEST_CONTROL = 1" >>vasl_templates/webapp/config/debug.cfg ; fi

EXPOSE 5010
COPY docker/run.sh .
CMD ./run.sh
