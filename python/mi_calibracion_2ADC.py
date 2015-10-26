# Script for ADC ASIAA 5GSP calibration in ROACH 2

import numpy as np
import adc5g as adc
import corr
import time
import sys
import struct
import pylab
import fit_cores
import rww_tools
import scipy.optimize
import scipy

# sampling time
frec_samp = 2400

################   START OF MAIN   ################

if __name__ == '__main__':
    from optparse import OptionParser

    p = OptionParser()
    #p.set_usage('%prog [options]')
    #p.set_usage('spectrometer.py [options]')
    p.set_description(__doc__)
    p.add_option('-p', '--skip_prog', dest='prog_fpga',action='store_false', default=True,
        help='Skip FPGA programming (assumes already programmed).  Default: program the FPGAs')
    #p.add_option('-e', '--skip_eq', dest='prog_eq',action='store_false', default=True, 
    #    help='Skip configuration of the equaliser in the F engines.  Default: set the EQ according to config file.')
    p.add_option('-v', '--verbosity', dest='verbosity',type='int', default=0,
        help='Verbosity level. Default: 0')
    p.add_option('-r', '--roach', dest='roach',type='str', default='192.168.1.12',
        help='ROACH IP address or hostname. Default: 192.168.1.12')
    p.add_option('-b', '--boffile', dest='boffile',type='str', default='cal_2adc_2015_Jan_16_1157.bof',
        help='Boffile to program. Default: ami_fx_sbl_wide.bof')
    p.add_option('-N', '--n_trials', dest='n_trials',type='int', default=2,
        help='Number of snap/fit trials. Default: 2')
    p.add_option('-c', '--clockrate', dest='clockrate', type='float', default=None,
        help='Clock rate in MHz, for use when plotting frequency axes. If none is given, rate will be estimated from FPGA clock')
    p.add_option('-f', '--testfreq', dest='testfreq', type='float', default=10.0,
        help='sine wave test frequency input in MHz. Default = 10')
    #p.add_option('-z', '--zdok', dest='zdok', type='int', default=1,
    #    help='ZDOK where the ADC is connected. Default = 1')

    opts, args = p.parse_args(sys.argv[1:])
	
    # ROACH 2 connection
    print 'Connecting to %s'%opts.roach
    fpga = corr.katcp_wrapper.FpgaClient(opts.roach,7147)
    time.sleep(0.2)
    print 'ROACH is connected?', fpga.is_connected()
    
    # ADC clock speed estimetion
    print 'Estimating clock speed...'
    clk_est = fpga.est_brd_clk()
    print 'Clock speed is %d MHz'%clk_est
    if opts.clockrate is None:
        clkrate = clk_est*16	# Must be equal to ADC sampling time in interleave mode (5gs)
    else:
        clkrate = opts.clockrate
        
    print 'Calibrating the time delay at the adc interface...'	
    opt0, glitches0 = adc.calibrate_mmcm_phase(fpga, 0, ['snapshot0',])
    opt1, glitches1 = adc.calibrate_mmcm_phase(fpga, 1, ['snapshot1',])
    time.sleep(0.5)

    ##################################################################
    ################### CALIBRATION ZDOK1 ############################
    ##################################################################
    
    # rwwtools parameters to use
    rww_tools.roach2 = fpga
    rww_tools.freq = opts.testfreq
    rww_tools.snap_name='snapshot1' 	# ADC snapshot name
    rww_tools.samp_freq=frec_samp		# ADC interleave mode sample rate
    FNAME = 'snapshot_adc1_raw.dat'
    rww_tools.zdok = 1          		# ADC to calibrate

    # FPGA is proggramed with selected boffile
    if opts.prog_fpga:
        print 'Programming ROACH with boffile %s'%opts.boffile
        fpga.progdev(opts.boffile)
        time.sleep(0.5)

    # ADC offset, gain and phase registers are creared
    print 'Clearing OGP registers...'
    rww_tools.clear_ogp()
    #print 'sleeping for 5s'
    time.sleep(2)

    # print registers
    print 'OGP registers:  '
    rww_tools.get_ogp()
  

    # OFFSET - GAIN - PHASE Calibration

    print 'Doing OGP calibration...'
    #ogp, sinad = rww_tools.dosnap(fr=opts.testfreq,name=FNAME,rpt=opts.n_trials,donot_clear=False)

    # calibration parameters
    rpt = 30	# repetitions until set of offset, ganancia y fase
    snap_name='snapshot1' 	# ADC snapshot name
    samp_freq=frec_samp		# ADC interleave mode sample rate
    FNAME = 'snapshot_adc1_raw.dat'
    avg_pwr_sinad = 0
    fr = opts.testfreq
    donot_clear = False

    for i in range(rpt):
        snap=adc.get_snapshot(fpga, snap_name, man_trig=True, wait_period=2)
        np.savetxt(FNAME, snap,fmt='%d')
        ogp, pwr_sinad = fit_cores.fit_snap(fr, samp_freq, FNAME,\
       	    clear_avgs = i == 0 and not donot_clear, prnt = i == rpt-1)
   	avg_pwr_sinad += pwr_sinad

    sinad = avg_pwr_sinad/rpt 

    ogp = ogp[3:]

    np.savetxt('ogp',ogp,fmt='%8.4f')

    # print registers
    print 'OGP registers:  '
    rww_tools.get_ogp()
  

    print 'Setting ogp'

    t = np.genfromtxt('ogp')

    rww_tools.set_offs(t[0], t[3], t[6], t[9])
    rww_tools.set_gains(t[1], t[4], t[7], t[10])
    rww_tools.set_phase(t[2], t[5], t[8], t[11])
    
    print 'OGP registers ADC 1:  '
    rww_tools.zdok = 1	# set ADC to calibrate

    rww_tools.get_ogp()

# INL CORRECTIONS
   
    textname = 'snapshot_adc1_raw.dat.res'

    print 'INL corrections correction... '
    rww_tools.clear_inl()
    rww_tools.get_inl()
    fit_cores.fit_inl(textname)
    
    rww_tools.set_inl('inl.meas')

    print 'INL registers: '
    rww_tools.get_inl()

    print 'done'

    ##################################################################
    ################### CALIBRACION ZDOK0 ############################
    ##################################################################
    
    # rwwtools parameters to use
    rww_tools.roach2 = fpga
    rww_tools.freq = opts.testfreq
    rww_tools.snap_name='snapshot0' 	# ADC snapshot name
    rww_tools.samp_freq=frec_samp		# ADC interleave mode sample rate
    FNAME = 'snapshot_adc0_raw.dat'
    rww_tools.zdok = 0          		#  ADC to calibrate


    # Se limpian los registros de offset, ganancia y fase del ADC
    print 'Clearing OGP registers...'
    rww_tools.clear_ogp()
    time.sleep(2)

    # print registers
    print 'OGP registers:  '
    rww_tools.get_ogp()

    #OFFSET - GAIN - PHASE Calibration

    print 'Doing OGP calibration...'

    # calibration parameters 
    rpt = 30	# repetitions until set of offset, gain y phase
    snap_name='snapshot0' 	# ADC snapshot name
    samp_freq=frec_samp		#  ADC interleave mode sample rate
    FNAME = 'snapshot_adc0_raw.dat'
    avg_pwr_sinad = 0
    fr = opts.testfreq
    donot_clear = False

    for i in range(rpt):
        snap=adc.get_snapshot(fpga, snap_name, man_trig=True, wait_period=2)
        np.savetxt(FNAME, snap,fmt='%d')
        ogp, pwr_sinad = fit_cores.fit_snap(fr, samp_freq, FNAME,\
       	    clear_avgs = i == 0 and not donot_clear, prnt = i == rpt-1)
   	avg_pwr_sinad += pwr_sinad

    sinad = avg_pwr_sinad/rpt 

    ogp = ogp[3:]

    np.savetxt('ogp',ogp,fmt='%8.4f')

    # print registers
    print 'OGP registers:  '
    rww_tools.get_ogp()
  

    print 'Setting ogp'
    t = np.genfromtxt('ogp')

    rww_tools.set_offs(t[0], t[3], t[6], t[9])
    rww_tools.set_gains(t[1], t[4], t[7], t[10])
    rww_tools.set_phase(t[2], t[5], t[8], t[11])
    
    print 'OGP registers ADC 1:  '
    rww_tools.zdok = 0	# set ADC to calibrate

    rww_tools.get_ogp()

    # INL CORRECTIONS
   
    textname = 'snapshot_adc0_raw.dat.res'

    print 'INL corrections correction... '
    rww_tools.clear_inl()
    rww_tools.get_inl()
    fit_cores.fit_inl(textname)
    
    rww_tools.set_inl('inl.meas')

    print 'INL registers: '
    rww_tools.get_inl()

    print 'done'
    
    exit()

