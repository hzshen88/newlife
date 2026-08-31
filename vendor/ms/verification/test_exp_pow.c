#include <stdio.h>
#include <math.h>
#include <stdint.h>
int main() {
    double u[] = {0.5, 1.23456, 2.9, 0.001, -0.5, -3.7};
    for (int i = 0; i < 6; i++) {
        double r = exp(-u[i]);
        uint64_t bits; __builtin_memcpy(&bits, &r, 8);
        printf("exp(%.17g) = %.17g bits=%016llx\n", -u[i], r, (unsigned long long)bits);
    }
    double pc = 0.998; double n = 47.0;
    double r2 = pow(pc, n);
    uint64_t bits2; __builtin_memcpy(&bits2, &r2, 8);
    printf("pow(%.17g,%.17g) = %.17g bits=%016llx\n", pc, n, r2, (unsigned long long)bits2);
    return 0;
}
