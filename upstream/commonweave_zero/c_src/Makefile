CC = gcc
CFLAGS = -O2 -fPIC -std=c99 -Wall -Wextra
LDFLAGS = -shared

all: libmatmul.so libstats.so

libmatmul.so: matmul.c matmul.h
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ matmul.c -lm

libstats.so: stats.c stats.h
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ stats.c

clean:
	rm -f libmatmul.so libstats.so

.PHONY: all clean
