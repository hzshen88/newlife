#include <stdio.h>
#include <math.h>
#include <stdint.h>

int poisso(double u, double ru, double *cump_out) {
    double cump, p;
    int i = 1;
    p = exp(-u);
    if (ru < p) { *cump_out = p; return 0; }
    cump = p;
    while (ru > (cump += (p *= u/i)))
        i++;
    *cump_out = cump;
    return i;
}

int main() {
    for (double u = 0.5; u < 29.5; u += 0.5) {
        for (double ru = 0.0001; ru < 0.9999; ru += 0.0005) {
            double cump;
            int i = poisso(u, ru, &cump);
            uint64_t bits; __builtin_memcpy(&bits, &cump, 8);
            printf("%.4f %.4f %d %016llx\n", u, ru, i, (unsigned long long)bits);
        }
    }
    return 0;
}
