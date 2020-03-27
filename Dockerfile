# NOTE: Use the run-container.sh script to build and launch this container.

FROM python:alpine3.6

# NOTE: pillow needs zlib and jpeg, lxml needs libxslt, we need build-base for gcc, etc.
RUN apk add --no-cache build-base zlib-dev jpeg-dev libxslt-dev
ENV LIBRARY_PATH=/lib:/usr/lib

WORKDIR /app

ARG ENABLE_TESTS

# install the Python requirements
COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements.txt ; \
    if [ "$ENABLE_TESTS" ]; then pip install -r requirements-dev.txt ; fi

# install the application
ADD vasl_templates vasl_templates
COPY setup.py LICENSE.txt ./
RUN pip install -e .

# copy the config files
COPY docker/config/* vasl_templates/webapp/config/
RUN if [ "$ENABLE_TESTS" ]; then echo "ENABLE_REMOTE_TEST_CONTROL = 1" >>vasl_templates/webapp/config/debug.cfg ; fi

EXPOSE 5010
COPY docker/run.sh .
CMD ./run.sh
