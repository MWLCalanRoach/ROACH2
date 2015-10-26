#!/usr/bin/env python
'''
Este script grafica un Snapshot de los ADC5g de la ROACH-2. Sirve para calibrar los ADC!! La idea es graficar una senal de 10MHz.

\nAuthor: Andres Alvear, Junio 2014.
'''

import corr,time,struct,sys,logging,pylab,matplotlib,math,Gnuplot, Gnuplot.funcutils,array
from math import *
import adc5g
import numpy

#bitstream = 'No_bof_file_error'
bitstream = 'adc5g_r2_offsetbin_signed_2014_Jul_03_1302.bof'
katcp_port=7147

def creartxt():
    archi=open('datos_ADC0.dat','w')
    archi.close()
    archi1=open('datos_ADC1.dat','w')
    archi1.close()

archi=open('datos_ADC0.dat','a')
archi1=open('datos_ADC1.dat','a')
creartxt()

def exit_fail():
    print 'FAILURE DETECTED. Log entries:\n',lh.printMessages()
    try:
        fpga.stop()
    except: pass
    raise
    exit()

def exit_clean():
    try:
        fpga.stop()
    except: pass
    exit()

hola = []
hola1 = []

def get_data():
    #get the data... 
    hola = numpy.array(adc5g.get_snapshot(fpga, "snapshot0"))
    hola1 = numpy.array(adc5g.get_snapshot(fpga, "snapshot1"))
    #    raw_1 = numpy.array(adc5g.get_snapshot(fpga, "raw_1"))
    return hola, hola1

def continuous_plot(fpga):
        ok=1
        bw=trunc(fpga.est_brd_clk())*8
        
	g0.clear()    
        g0.title('ADC0 Snapshot of a low frequency (10 MHz)'+bitstream+' | Max frequency = '+str(bw)+' MHz')
        g0.xlabel('Sample number')
        g0.ylabel('ADC output')
        g0('set style data linespoints')
	g0('set yrange [-130:130]')
	g0('set xrange [0:500]')
	g0('set ytics 5')
	g0('set xtics 32')
	g0('set grid y')
	g0('set grid x')

	g1.clear()    
        g1.title('ADC1 Snapshot of a low frequency (10 MHz)'+bitstream+' | Max frequency = '+str(bw)+' MHz')
        g1.xlabel('Sample number')
        g1.ylabel('ADC output')
        g1('set style data linespoints')
	g1('set yrange [-130:130]')
	g1('set xrange [0:500]')
	g1('set ytics 5')
	g1('set xtics 32')
	g1('set grid y')
	g1('set grid x')	

        while ok==1 :
		hola, hola1= get_data()
		g0.plot(hola)
		time.sleep(0.3)
		g1.plot(hola1)
		time.sleep(0.3)


################   START OF MAIN   ################

if __name__ == '__main__':
    from optparse import OptionParser


    p = OptionParser()
    p.set_usage('spectrometer.py <ROACH_HOSTNAME_or_IP> [options]')
    p.set_description(__doc__)
    p.add_option('-s', '--skip', dest='skip', action='store_true',
        help='Skip reprogramming the FPGA and configuring EQ.')
    p.add_option('-b', '--bof', dest='boffile',type='str', default='',
        help='Specify the bof file to load')
    opts, args = p.parse_args(sys.argv[1:])

    if args==[]:
        print 'Please specify a ROACH board. Run with the -h flag to see all options.\nExiting.'
        exit()
    else:
        roach = args[0] 
    if opts.boffile != '':
        bitstream = opts.boffile

try:
    loggers = []
    lh=corr.log_handlers.DebugLogHandler()
    logger = logging.getLogger(roach)
    logger.addHandler(lh)
    logger.setLevel(10)

    print('Connecting to server %s on port %i... '%(roach,katcp_port)),
    fpga = corr.katcp_wrapper.FpgaClient(roach, katcp_port, timeout=10,logger=logger)
    time.sleep(1)

    if fpga.is_connected():
        print 'ok\n'
    else:
        print 'ERROR connecting to server %s on port %i.\n'%(roach,katcp_port)
        exit_fail()

    print '------------------------'
    print 'Programming FPGA with %s...' %bitstream,
    if not opts.skip:
        fpga.progdev(bitstream)
        print 'done'
    else:
        print 'Skipped.'
#
    print 'waiting 3 seconds...'
    time.sleep(3)

    #set up the figure with a subplot to be plotted
    g0 = Gnuplot.Gnuplot(debug=1)
    g1 = Gnuplot.Gnuplot(debug=1)

    hola, hola1 = get_data()
    numpy.savetxt(archi, hola, newline="\n")
    numpy.savetxt(archi1, hola1, newline="\n")
    continuous_plot(fpga)

    print 'Plot started.'

except KeyboardInterrupt:
    exit_clean()
except:
    exit_fail()

exit_clean()
