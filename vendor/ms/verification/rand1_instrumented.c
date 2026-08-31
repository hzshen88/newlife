/* Instrumented copy of vendor/ms/rand1.c for draw-tracing verification.
 *
 * NOT the vendored oracle — the pristine rand1.c (SHA-256 pinned in
 * test_ms_vendor.py) is never modified. This file adds append-only draw
 * logging to ran1() and changes nothing else: the arithmetic, the seed
 * handling, and every other line are copied verbatim from rand1.c. Log
 * path is read from the MS_DRAW_LOG environment variable; if unset,
 * logging is a no-op and this file computes bit-for-bit the same values
 * as the vendored rand1.c.
 *
 * Per the second-world question doc's ruling ("Draw parity" / open
 * question 4): draw tracing is done by instrumenting rand1.c and
 * rebuilding, not by hand-transcribing streec.c/ms.c's call sites into a
 * static list.
 */

#include <stdio.h>
#include <stdlib.h>

static FILE *draw_log = NULL;
static int draw_log_checked = 0;

static void draw_log_open_if_needed(void) {
    if (!draw_log_checked) {
        draw_log_checked = 1;
        const char *path = getenv("MS_DRAW_LOG");
        if (path != NULL) {
            draw_log = fopen(path, "w");
        }
    }
}

         double
ran1()
{
        double drand48();
        double r = drand48();
        draw_log_open_if_needed();
        if (draw_log != NULL) {
            fprintf(draw_log, "%.20g\n", r);
        }
        return( r );
}


	void seedit( char *flag )
{
	FILE *fopen(), *pfseed;
	unsigned short seedv[3], seedv2[3],  *seed48(), *pseed ;
	int i;

	if( flag[0] == 's' ) {
	   pfseed = fopen("seedms","r");
	   if( pfseed == NULL ) {
           seedv[0] = 3579 ; seedv[1] = 27011; seedv[2] = 59243;
	   }
	   else {
	       seedv2[0] = 3579; seedv2[1] = 27011; seedv2[2] = 59243;
           for(i=0;i<3;i++){
		       if(  fscanf(pfseed," %hd",seedv+i) < 1 )
		            seedv[i] = seedv2[i] ;
		   }
	       fclose( pfseed);
	   }
	   seed48( seedv );

       printf("\n%d %d %d\n", seedv[0], seedv[1], seedv[2] );
	}
	else {
	     pfseed = fopen("seedms","w");
         pseed = seed48(seedv);
         fprintf(pfseed,"%d %d %d\n",pseed[0], pseed[1],pseed[2]);
	}
}

	int
commandlineseed( char **seeds)
{
	unsigned short seedv[3], *seed48();

	seedv[0] = atoi( seeds[0] );
	seedv[1] = atoi( seeds[1] );
	seedv[2] = atoi( seeds[2] );
	printf("\n%d %d %d\n", seedv[0], seedv[1], seedv[2] );

	seed48(seedv);
	return(3);
}
