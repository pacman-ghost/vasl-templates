#!/usr/bin/env bash
# Helper script that builds and launches the Docker container.

# ---------------------------------------------------------------------

function main
{
    # initialize
    cd `dirname "$0"`
    PORT=5010
    VASSAL=
    VASL_MOD=
    VASL_EXTNS=
    VASL_BOARDS=
    CHAPTER_H_NOTES=
    USER_FILES=
    TEMPLATE_PACK=
    IMAGE_TAG=latest
    CONTAINER_NAME=vasl-templates
    DETACH=
    NO_BUILD=
    BUILD_ARGS=
    BUILD_NETWORK=
    RUN_NETWORK=
    CONTROL_TESTS_PORT=
    TEST_DATA_VASSAL=
    TEST_DATA_VASL_MODS=

    # parse the command-line arguments
    if [ $# -eq 0 ]; then
        print_help
        exit 0
    fi
    params="$(getopt -o p:v:e:k:t:d -l port:,control-tests-port:,vassal:,vasl:,vasl-extensions:,boards:,chapter-h:,template-pack:,user-files:,tag:,name:,detach,no-build,build-arg:,build-network:,run-network:,test-data-vassal:,test-data-vasl-mods:,help --name "$0" -- "$@")"
    if [ $? -ne 0 ]; then exit 1; fi
    eval set -- "$params"
    while true; do
        case "$1" in
            -p | --port)
                PORT=$2
                shift 2 ;;
            --vassal)
                VASSAL=$2
                shift 2 ;;
            -v | --vasl)
                VASL_MOD=$2
                shift 2 ;;
            -e | --vasl-extensions)
                VASL_EXTNS=$2
                shift 2 ;;
            --boards)
                VASL_BOARDS=$2
                shift 2 ;;
            --chapter-h)
                CHAPTER_H_NOTES=$2
                shift 2 ;;
            --user-files)
                USER_FILES=$2
                shift 2 ;;
            -k | --template-pack)
                TEMPLATE_PACK=$2
                shift 2 ;;
            -t | --tag)
                IMAGE_TAG=$2
                shift 2 ;;
            --name)
                CONTAINER_NAME=$2
                shift 2 ;;
            -d | --detach )
                DETACH=--detach
                shift 1 ;;
            --no-build )
                NO_BUILD=1
                shift 1 ;;
            --build-arg )
                BUILD_ARGS="$BUILD_ARGS --build-arg $2"
                shift 2 ;;
            --build-network )
                # FUDGE! We sometimes can't get out to the internet from the container (DNS problems) using the default
                # "bridge" network, so we offer the option of using an alternate network (e.g. "host").
                BUILD_NETWORK="--network $2"
                shift 2 ;;
            --run-network )
                RUN_NETWORK="--network $2"
                shift 2 ;;
            --control-tests-port)
                CONTROL_TESTS_PORT=$2
                shift 2 ;;
            --test-data-vassal )
                target=$( realpath --no-symlinks "$2" )
                TEST_DATA_VASSAL="--volume $target:/test-data/vassal/"
                shift 2 ;;
            --test-data-vasl-mods )
                target=$( realpath --no-symlinks "$2" )
                TEST_DATA_VASL_MODS="--volume $target:/test-data/vasl-mods/"
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
    if [ -n "$VASSAL" ]; then
        target=$( get_target DIR "$VASSAL" )
        if [ -z "$target" ]; then
            echo "Can't find the VASSAL directory: $VASSAL"
            exit 1
        fi
        mpoint=/data/vassal/
        VASSAL_VOLUME="--volume $target:$mpoint"
        VASSAL_ENV="--env VASSAL_DIR=$mpoint --env VASSAL_DIR_TARGET=$target"
    fi

    # check if a VASL module file has been specified
    if [ -n "$VASL_MOD" ]; then
        target=$( get_target FILE "$VASL_MOD" )
        if [ -z "$target" ]; then
            echo "Can't find the VASL .vmod file: $VASL_MOD"
            exit 1
        fi
        mpoint=/data/vasl.vmod
        VASL_MOD_VOLUME="--volume $target:$mpoint"
        VASL_MOD_ENV="--env VASL_MOD=$mpoint --env VASL_MOD_TARGET=$target"
    fi

    # check if a VASL extensions directory has been specified
    if [ -n "$VASL_EXTNS" ]; then
        target=$( get_target DIR "$VASL_EXTNS" )
        if [ -z "$target" ]; then
            echo "Can't find the VASL extensions directory: $VASL_EXTNS"
            exit 1
        fi
        mpoint=/data/vasl-extensions/
        VASL_EXTNS_VOLUME="--volume $target:$mpoint"
        VASL_EXTNS_ENV="--env VASL_EXTNS_DIR=$mpoint --env VASL_EXTNS_DIR_TARGET=$target"
    fi

    # check if a VASL boards directory has been specified
    if [ -n "$VASL_BOARDS" ]; then
        target=$( get_target DIR "$VASL_BOARDS" )
        if [ -z "$target" ]; then
            echo "Can't find the VASL boards directory: $VASL_BOARDS"
            exit 1
        fi
        mpoint=/data/boards/
        VASL_BOARDS_VOLUME="--volume $target:$mpoint"
        VASL_BOARDS_ENV="--env BOARDS_DIR=$mpoint --env BOARDS_DIR_TARGET=$target"
    fi

    # check if a Chapter H notes directory has been specified
    if [ -n "$CHAPTER_H_NOTES" ]; then
        target=$( get_target DIR "$CHAPTER_H_NOTES" )
        if [ -z "$target" ]; then
            echo "Can't find the Chapter H notes directory: $CHAPTER_H_NOTES"
            exit 1
        fi
        mpoint=/data/chapter-h-notes/
        CHAPTER_H_NOTES_VOLUME="--volume $target:$mpoint"
        CHAPTER_H_NOTES_ENV="--env CHAPTER_H_NOTES_DIR=$mpoint --env CHAPTER_H_NOTES_DIR_TARGET=$target"
    fi

    # check if a user files directory has been specified
    if [ -n "$USER_FILES" ]; then
        target=$( get_target DIR "$USER_FILES" )
        if [ -z "$target" ]; then
            echo "Can't find the user files directory: $USER_FILES"
            exit 1
        fi
        mpoint=/data/user-files/
        USER_FILES_VOLUME="--volume $target:$mpoint"
        USER_FILES_ENV="--env USER_FILES_DIR=$mpoint --env USER_FILES_DIR_TARGET=$target"
    fi

    # check if a template pack has been specified
    if [ -n "$TEMPLATE_PACK" ]; then
        # NOTE: The template pack can either be a file (ZIP) or a directory.
        target=$( get_target FILE-OR-DIR "$TEMPLATE_PACK" )
        if [ -z "$target" ]; then
            echo "Can't find the template pack: $TEMPLATE_PACK"
            exit 1
        fi
        mpoint=/data/template-pack
        TEMPLATE_PACK_VOLUME="--volume $target:$mpoint"
        TEMPLATE_PACK_ENV="--env DEFAULT_TEMPLATE_PACK=$mpoint --env DEFAULT_TEMPLATE_PACK_TARGET"
    fi

    # check if testing has been enabled
    if [ -n "$CONTROL_TESTS_PORT" ]; then
        BUILD_ARGS="$BUILD_ARGS --build-arg CONTROL_TESTS_PORT=$CONTROL_TESTS_PORT"
        CONTROL_TESTS_PORT_RUN="--env CONTROL_TESTS_PORT=$CONTROL_TESTS_PORT --publish $CONTROL_TESTS_PORT:$CONTROL_TESTS_PORT"
    fi

    # build the image
    if [ -z "$NO_BUILD" ]; then
        echo Building the \"$IMAGE_TAG\" image...
        docker build \
            --tag vasl-templates:$IMAGE_TAG \
            $BUILD_ARGS \
            $BUILD_NETWORK \
            . 2>&1 \
          | sed -e 's/^/  /'
        if [ ${PIPESTATUS[0]} -ne 0 ]; then exit 10 ; fi
        echo
    fi

    # launch the container
    echo Launching the \"$IMAGE_TAG\" image as \"$CONTAINER_NAME\"...
    docker run \
        --name $CONTAINER_NAME \
        --publish $PORT:5010 \
        --env DOCKER_IMAGE_NAME="vasl-templates:$IMAGE_TAG" \
        --env DOCKER_IMAGE_TIMESTAMP="$(date --utc +"%Y-%m-%d %H:%M:%S %:z")" \
        --env BUILD_GIT_INFO="$(get_git_info)" \
        --env DOCKER_CONTAINER_NAME="$CONTAINER_NAME" \
        $CONTROL_TESTS_PORT_RUN \
        $VASSAL_VOLUME $VASL_MOD_VOLUME $VASL_EXTNS_VOLUME $VASL_BOARDS_VOLUME $CHAPTER_H_NOTES_VOLUME $TEMPLATE_PACK_VOLUME $USER_FILES_VOLUME \
        $VASSAL_ENV $VASL_MOD_ENV $VASL_EXTNS_ENV $VASL_BOARDS_ENV $CHAPTER_H_NOTES_ENV $TEMPLATE_PACK_ENV $USER_FILES_ENV \
        $RUN_NETWORK $DETACH \
        $TEST_DATA_VASSAL $TEST_DATA_VASL_MODS \
        -it --rm \
        vasl-templates:$IMAGE_TAG \
        2>&1 \
      | sed -e 's/^/  /'
    exit ${PIPESTATUS[0]}
}

# ---------------------------------------------------------------------

function get_git_info {
    # NOTE: We assume the source code has a git repo, and git is installed, etc. etc., which should
    # all be true, but in the event we can't get the current branch and commit ID, we return nothing,
    # and nothing will be shown in the Program Info dialog in the UI.
    cd "${0%/*}"
    local branch=$( git branch | grep "^\*" | cut -c 3- )
    local commit=$( git log | head -n 1 | cut -f 2 -d " " | cut -c 1-8 )
    if [[ -n "$branch" && -n "$commit" ]]; then
        echo "$branch:$commit"
    fi
}

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function get_target {
    local type=$1
    local target=$2

    # check that the target exists
    if [ "$type" == "FILE" ]; then
        test -f "$target" || return
    elif [ "$type" == "DIR" ]; then
        test -d "$target" || return
    elif [ "$type" == "FILE-OR-DIR" ]; then
        ls "$target" >/dev/null 2>&1 || return
    fi

    # convert the target to a full path
    # FUDGE! I couldn't get the "docker run" command to work with spaces in the volume targets (although
    # copying the generated command into the terminal worked fine) (and no, using ${var@Q} didn't help).
    # So, the next best thing is to allow users to create symlinks to the targets :-/
    echo $( realpath --no-symlinks "$target" )
}

# ---------------------------------------------------------------------

function print_help {
    echo "`basename "$0"` {options}"
    cat <<EOM
  Build and launch the "vasl-templates" container.

    -p  --port             Web server port number.
        --vassal           VASSAL installation directory.
    -v  --vasl             Path to the VASL module file (.vmod).
    -e  --vasl-extensions  Path to the VASL extensions directory.
        --boards           Path to the VASL boards.
        --chapter-h        Path to the Chapter H notes directory.
        --user-files       Path to the user files directory.
    -k  --template-pack    Path to a user-defined template pack.

    -t  --tag              Docker image tag.
        --name             Docker container name.
    -d  --detach           Detach from the container and let it run in the background.
        --no-build         Launch the container as-is (i.e. without rebuilding the image first).
        --build-network    Docker network to use when building the image.
        --run-network      Docker network to use when running the container.

    Options for the test suite:
      --control-tests-port   Remote test control port number.
      --test-data-vassal     Directory containing VASSAL releases.
      --test-data-vasl-mods  Directory containing VASL modules.

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

main "$@"
