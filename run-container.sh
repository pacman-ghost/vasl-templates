#!/usr/bin/env bash
# Helper script that builds and launches the Docker container.

# ---------------------------------------------------------------------

function print_help {
    echo "`basename "$0"` {options}"
    echo "  Build and launch the \"vasl-templates\" container."
    echo
    echo "    -p  --port             Web server port number."
    echo "    -v  --vasl-vmod        Path to the VASL .vmod file."
    echo "    -e  --vasl-extensions  Path to the VASL extensions directory."
    echo "    -h  --chapter-h        Path to the Chapter H notes directory."
    echo
    echo "    -t  --tag              Docker tag."
    echo "    -d  --detach           Detach from the container and let it run in the background."
    echo "        --no-build         Launch the container as-is (i.e. without rebuilding it first)."
}

# ---------------------------------------------------------------------

# initialize
cd `dirname "$0"`
PORT=5010
VASL_MOD_LOCAL=
VASL_MOD=
VASL_EXTNS_LOCAL=
VASL_EXTNS=
CHAPTER_H_NOTES_LOCAL=
CHAPTER_H_NOTES=
TAG=latest
DETACH=
NO_BUILD=

# parse the command-line arguments
if [ $# -eq 0 ]; then
    print_help
    exit 0
fi
params="$(getopt -o p:v:e:h:t:d -l port:,vasl-vmod:,vasl-extensions:,chapter-h:,tag:,detach,no-build,help --name "$0" -- "$@")"
if [ $? -ne 0 ]; then exit 1; fi
eval set -- "$params"
while true; do
    case "$1" in
        -p | --port)
            PORT=$2
            shift 2 ;;
        -v | --vasl-vmod)
            VASL_MOD_LOCAL=$2
            shift 2 ;;
        -e | --vasl-extensions)
            VASL_EXTNS_LOCAL=$2
            shift 2 ;;
        -h | --chapter-h)
            CHAPTER_H_NOTES_LOCAL=$2
            shift 2 ;;
        -t | --tag)
            TAG=$2
            shift 2 ;;
        -d | --detach )
            DETACH=--detach
            shift 1 ;;
        --no-build )
            NO_BUILD=1
            shift 1 ;;
        --help )
            print_help
            exit 0 ;;
        -- ) shift ; break ;;
        * )
            echo "Unknown option: $1" >&2
            exit 1 ;;
    esac
done

# check if a VASL .vmod file has been specified
if [ -n "$VASL_MOD_LOCAL" ]; then
    if [ ! -f "$VASL_MOD_LOCAL" ]; then
        echo "Can't find the VASL .vmod file: $VASL_MOD_LOCAL"
        exit 1
    fi
    VASL_MOD=/data/vasl.vmod
    VASL_MOD_VOLUME="--volume `readlink -f "$VASL_MOD_LOCAL"`:$VASL_MOD"
    VASL_MOD_ENV="--env VASL_MOD=$VASL_MOD"
fi

# check if a VASL extensions directory has been specified
if [ -n "$VASL_EXTNS_LOCAL" ]; then
    if [ ! -d "$VASL_EXTNS_LOCAL" ]; then
        echo "Can't find the VASL extensions directory: $_EXTNS_DIR_LOCAL"
        exit 1
    fi
    VASL_EXTNS=/data/vasl-extensions/
    VASL_EXTNS_VOLUME="--volume `readlink -f "$VASL_EXTNS_LOCAL"`:$VASL_EXTNS"
    VASL_EXTNS_ENV="--env VASL_EXTNS_DIR=$VASL_EXTNS"
fi

# check if a Chapter H notes directory has been specified
if [ -n "$CHAPTER_H_NOTES_LOCAL" ]; then
    if [ ! -d "$CHAPTER_H_NOTES_LOCAL" ]; then
        echo "Can't find the Chapter H notes directory: $CHAPTER_H_NOTES_LOCAL"
        exit 1
    fi
    CHAPTER_H_NOTES=/data/chapter-h-notes/
    CHAPTER_H_NOTES_VOLUME="--volume `readlink -f "$CHAPTER_H_NOTES_LOCAL"`:$CHAPTER_H_NOTES"
    CHAPTER_H_NOTES_ENV="--env CHAPTER_H_NOTES_DIR=$CHAPTER_H_NOTES"
fi

# build the container
if [ -z "$NO_BUILD" ]; then
    echo Building the container...
    docker build . --tag vasl-templates:$TAG 2>&1 \
        | sed -e 's/^/  /'
    if [ $? -ne 0 ]; then exit 10 ; fi
    echo
fi

# launch the container
echo Launching the container...
docker run \
    --publish $PORT:5010 \
    --name vasl-templates \
    $VASL_MOD_VOLUME $VASL_EXTNS_VOLUME $CHAPTER_H_NOTES_VOLUME \
    $VASL_MOD_ENV $VASL_EXTNS_ENV $CHAPTER_H_NOTES_ENV \
    $DETACH \
    -it --rm \
    vasl-templates:$TAG \
    2>&1 \
| sed -e 's/^/  /'
