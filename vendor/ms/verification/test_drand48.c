#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
int main() {
    unsigned short seedv[3] = {3579, 27011, 59243};
    seed48(seedv);
    for (int i = 0; i < 8; i++) {
        double r = drand48();
        uint64_t bits; __builtin_memcpy(&bits, &r, 8);
        printf("drand48()[%d] = %.17g  bits=%016llx\n", i, r, (unsigned long long)bits);
    }
    return 0;
}
