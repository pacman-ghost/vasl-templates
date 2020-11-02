# Define VASSAL_DIR in the command line arguments to point to the directory that contains Vengine.jar e.g.
#   make all VASSAL_DIR=...
# We are currently compiling with Java 14.0.2, using VASSAL 3.4.2.

SRC_DIR:=src
DATA_DIR:=data
OUTPUT_DIR:=output
RELEASE_DIR:=release

JAVAC:=javac
JAR:=jar
CLASSPATH:=$(VASSAL_DIR)/Vengine.jar:$(OUTPUT_DIR)
JAVAC_FLAGS:=-d $(OUTPUT_DIR) -classpath $(CLASSPATH) -sourcepath $(SRC_DIR) -Xlint:unchecked

all: init compile

init:
	mkdir -p $(OUTPUT_DIR)
	mkdir -p $(RELEASE_DIR)

compile: init
	$(JAVAC) $(JAVAC_FLAGS) $(shell find $(SRC_DIR) -name '*.java')
	cp -r $(DATA_DIR) $(OUTPUT_DIR)
	$(JAR) cfe $(RELEASE_DIR)/vassal-shim.jar vassal_shim.Main -C $(OUTPUT_DIR) .

clean:
	rm -r $(OUTPUT_DIR)
	rm -r $(RELEASE_DIR)
