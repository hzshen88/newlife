#include <stdio.h>
#include <math.h>
#include <stdint.h>
int main() {
    double vals[] = {0.123456789, 0.987654321, 0.5, 0.999999, 0.000001, 1.0, 0.3333333333333333};
    for (int i = 0; i < 7; i++) {
        double r = log(vals[i]);
        uint64_t bits;
        __builtin_memcpy(&bits, &r, 8);
        printf("log(%.17g) = %.17g  bits=%016llx\n", vals[i], r, (unsigned long long)bits);
    }
    return 0;
}
