#!/usr/bin/env bash
# Helper script that builds and launches the Docker container.

# ---------------------------------------------------------------------

function print_help {
    echo "`basename "$0"` {options}"
    cat <<EOM
  Build and launch the "vasl-templates" container.

    -p  --port             Web server port number.
        --vassal           VASSAL installation directory.
    -v  --vasl-vmod        Path to the VASL .vmod file.
    -e  --vasl-extensions  Path to the VASL extensions directory.
        --boards           Path to the VASL boards.
        --chapter-h        Path to the Chapter H notes directory.
        --user-files       Path to the user files directory.
    -k  --template-pack    Path to a user-defined template pack.

    -t  --tag              Docker tag.
    -d  --detach           Detach from the container and let it run in the background.
        --no-build         Launch the container as-is (i.e. without rebuilding it first).
        --build-network    Docker network to use when building the container.
        --run-network      Docker network to use when running the container.

NOTE: If the port the webapp server is listening on *inside* the container is different
to the port exposed *outside* the container, webdriver image generation (e.g. Shift-Click
on a snippet button, or Chapter H content as images) may not work properly. This is because
a web browser is launched internally with snippet HTML and a screenshot taken of it, but
the HTML will contain links to the webapp server that work from outside the container,
but if those links don't resolve from inside the container, you will get broken images.
In this case, you will need to make such links resolve from inside the container e.g. by
port-forwarding, or via DNS.
EOM
}

# ---------------------------------------------------------------------

# initialize
cd `dirname "$0"`
PORT=5010
VASSAL_LOCAL=
VASSAL=
VASL_MOD_LOCAL=
VASL_MOD=
VASL_BOARDS_LOCAL=
VASL_BOARDS=
VASL_EXTNS_LOCAL=
VASL_EXTNS=
CHAPTER_H_NOTES_LOCAL=
CHAPTER_H_NOTES=
TEMPLATE_PACK_LOCAL=
TEMPLATE_PACK=
USER_FILES_LOCAL=
USER_FILES=
TAG=latest
DETACH=
NO_BUILD=
BUILD_NETWORK=
RUN_NETWORK=

# parse the command-line arguments
if [ $# -eq 0 ]; then
    print_help
    exit 0
fi
params="$(getopt -o p:v:e:k:t:d -l port:,vassal:,vasl-vmod:,vasl-extensions:,boards:,chapter-h:,user-files:,template-pack:,tag:,detach,no-build,build-network:,run-network:,help --name "$0" -- "$@")"
if [ $? -ne 0 ]; then exit 1; fi
eval set -- "$params"
while true; do
    case "$1" in
        -p | --port)
            PORT=$2
            shift 2 ;;
        --vassal)
            VASSAL_LOCAL=$2
            shift 2 ;;
        -v | --vasl-vmod)
            VASL_MOD_LOCAL=$2
            shift 2 ;;
        -e | --vasl-extensions)
            VASL_EXTNS_LOCAL=$2
            shift 2 ;;
        --boards)
            VASL_BOARDS_LOCAL=$2
            shift 2 ;;
        --chapter-h)
            CHAPTER_H_NOTES_LOCAL=$2
            shift 2 ;;
        --user-files)
            USER_FILES_LOCAL=$2
            shift 2 ;;
        -k | --template-pack)
            TEMPLATE_PACK_LOCAL=$2
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
        --build-network )
            # FUDGE! We sometimes can't get out to the internet from the container (DNS problems) using the default
            # "bridge" network, so we offer the option of using an alternate network (e.g. "host").
            BUILD_NETWORK="--network $2"
            shift 2 ;;
        --run-network )
            RUN_NETWORK="--network $2"
            shift 2 ;;
        --help )
            print_help
            exit 0 ;;
        -- ) shift ; break ;;
        * )
            echo "Unknown option: $1" >&2
            exit 1 ;;
    esac
done

# check if a VASSAL directory has been specified
if [ -n "$VASSAL_LOCAL" ]; then
    if [ ! -d "$VASSAL_LOCAL" ]; then
        echo "Can't find the VASSAL directory: $VASSAL_LOCAL"
        exit 1
    fi
    VASSAL=/data/vassal/
    VASSAL_VOLUME="--volume `readlink -f "$VASSAL_LOCAL"`:$VASSAL"
    VASSAL_ENV="--env VASSAL_DIR=$VASSAL"
fi

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

# check if a VASL boards directory has been specified
if [ -n "$VASL_BOARDS_LOCAL" ]; then
    if [ ! -d "$VASL_BOARDS_LOCAL" ]; then
        echo "Can't find the VASL boards directory: $VASL_BOARDS_LOCAL"
        exit 1
    fi
    VASL_BOARDS=/data/boards/
    VASL_BOARDS_VOLUME="--volume `readlink -f "$VASL_BOARDS_LOCAL"`:$VASL_BOARDS"
    VASL_BOARDS_ENV="--env VASL_BOARDS_DIR=$VASL_BOARDS"
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

# check if a template pack has been specified
if [ -n "$TEMPLATE_PACK_LOCAL" ]; then
    # NOTE: The template pack can either be a file (ZIP) or a directory.
    if ! ls "$TEMPLATE_PACK_LOCAL" >/dev/null 2>&1 ; then
        echo "Can't find the template pack: $TEMPLATE_PACK_LOCAL"
        exit 1
    fi
    TEMPLATE_PACK=/data/template-pack
    TEMPLATE_PACK_VOLUME="--volume `readlink -f "$TEMPLATE_PACK_LOCAL"`:$TEMPLATE_PACK"
    TEMPLATE_PACK_ENV="--env DEFAULT_TEMPLATE_PACK=$TEMPLATE_PACK"
fi

# check if a user files directory has been specified
if [ -n "$USER_FILES_LOCAL" ]; then
    if [ ! -d "$USER_FILES_LOCAL" ]; then
        echo "Can't find the user files directory: $USER_FILES_LOCAL"
        exit 1
    fi
    USER_FILES=/data/user-files/
    USER_FILES_VOLUME="--volume `readlink -f "$USER_FILES_LOCAL"`:$USER_FILES"
    USER_FILES_ENV="--env USER_FILES_DIR=$USER_FILES"
fi

# build the container
if [ -z "$NO_BUILD" ]; then
    echo Building the \"$TAG\" container...
    docker build $BUILD_NETWORK --tag vasl-templates:$TAG . 2>&1 \
        | sed -e 's/^/  /'
    if [ ${PIPESTATUS[0]} -ne 0 ]; then exit 10 ; fi
    echo
fi

# launch the container
echo Launching the \"$TAG\" container...
docker run \
    --publish $PORT:5010 \
    --name vasl-templates \
    $VASSAL_VOLUME $VASL_MOD_VOLUME $VASL_BOARDS_VOLUME $VASL_EXTNS_VOLUME $CHAPTER_H_NOTES_VOLUME $USER_FILES_VOLUME $TEMPLATE_PACK_VOLUME \
    $VASSAL_ENV $VASL_MOD_ENV $VASL_BOARDS_ENV $VASL_EXTNS_ENV $CHAPTER_H_NOTES_ENV $USER_FILES_ENV $TEMPLATE_PACK_ENV \
    $RUN_NETWORK $DETACH \
    -it --rm \
    vasl-templates:$TAG \
    2>&1 \
| sed -e 's/^/  /'
exit ${PIPESTATUS[0]}
