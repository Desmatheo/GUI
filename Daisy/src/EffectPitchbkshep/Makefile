# Project Name
TARGET = PitchBksheperd

# Sources
# Use 'wildcard' to automatically find all .cpp files.
CPP_SOURCES = pitch_shifter_module.cpp \
              $(wildcard Util/*.cpp) \

# Library Locations
LIBDAISY_DIR = ../../libDaisy
DAISYSP_DIR = ../../DaisySP

# The Q library and std::span require modern C++
CPP_STANDARD = -std=gnu++20

# Add the current directory and Q library paths to the compiler's search path
C_INCLUDES += -I. -I./../Q/q_lib/include -I./../Q/infra/include -I./../gcem/include -I./include/CloudSeed 
C_INCLUDES += -I Util/

# Core location, and generic makefile.
SYSTEM_FILES_DIR = $(LIBDAISY_DIR)/core
include $(SYSTEM_FILES_DIR)/Makefile
