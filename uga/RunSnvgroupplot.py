## Copyright (c) 2015 Ryan Koesterer GNU General Public License v3
##
##    This program is free software: you can redistribute it and/or modify
##    it under the terms of the GNU General Public License as published by
##    the Free Software Foundation, either version 3 of the License, or
##    (at your option) any later version.
##
##    This program is distributed in the hope that it will be useful,
##    but WITHOUT ANY WARRANTY; without even the implied warranty of
##    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##    GNU General Public License for more details.
##
##    You should have received a copy of the GNU General Public License
##    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import pandas as pd
import numpy as np
import scipy.stats as scipy
import Parse
import pysam
import math
import Process
import readline
import rpy2.robjects as ro
import pandas.rpy.common as py2r
import logging
import re

logging.basicConfig(format='%(asctime)s - %(processName)s - %(name)s - %(message)s',level=logging.DEBUG)
logger = logging.getLogger("RunSnvplot")

def RunSnvgroupplot(args):
	cfg = Parse.generate_snvgroupplot_cfg(args)
	Parse.print_snvgroupplot_options(cfg)

	if not cfg['debug']:
		logging.disable(logging.CRITICAL)

	ro.r('suppressMessages(library(ggplot2))')
	ro.r('suppressMessages(library(grid))')

	handle=pysam.TabixFile(filename=cfg['file'],parser=pysam.asVCF())
	header = [x for x in handle.header]
	skip_rows = len(header)-1
	cols = header[-1].split()
	pcols = [x for x in cols if x == 'p' or len(re.findall('.p$',x)) > 0] if cfg['pcol'] is None else [cfg['pcol']]
	cmafcols = [x for x in cols if x == 'cmaf' or '.cmaf' in x] if cfg['pcol'] is None else [cfg['pcol'].replace('.p','.cmaf') if len(re.findall('.p$',cfg['pcol'])) > 0 else 'cmaf']
	cols_extract = ['#chr','start','end','id'] + pcols + cmafcols
	print "importing data"
	r = pd.read_table(cfg['file'],sep='\t',skiprows=skip_rows,usecols=cols_extract,compression='gzip')
	print str(r.shape[0]) + " total groups found"

	for pcol in pcols:
		if len(re.findall('.p$',pcol)) > 0:
			if pcol.replace('.p','.cmaf') in cmafcols:
				cmafcol = pcol.replace('.p','.cmaf')
			else:
				cmafcol = pcol.replace('.p','.cmafUsed')
		else:
			cmafcol = 'cmaf'
		print "plotting p-values for column " + pcol + " ..."
		results = r[['#chr','start','end','id',pcol,cmafcol]].copy()
		results.dropna(inplace=True)
		results = results[(results[pcol] > 0) & (results[pcol] <= 1)]
		if cfg['cmaf'] > 0:
			results = results[results[cmafcol] >= cfg['cmaf']]
		results.reset_index(drop=True, inplace=True)
		print "   " + str(results.shape[0]) + " groups with plottable p-values"

		results['logp'] = -1 * np.log10(results[pcol]) + 0.0
		results['pos'] = results.start + (results.end - results.start) / 2

		ro.globalenv['results'] = py2r.convert_to_r_dataframe(results, strings_as_factors=False)
		l = np.median(scipy.chi2.ppf([1-x for x in results[pcol].tolist()], df=1))/scipy.chi2.ppf(0.5,1)
		# in R: median(qchisq(results$p, df=1, lower.tail=FALSE))/qchisq(0.5,1)
		print "   genomic inflation (all variants) = " + str(l)

		if cfg['qq']:
			print "   generating standard qq plot"
			a = -1 * np.log10(ro.r('ppoints(' + str(len(results.index)) + ')'))
			a.sort_values(inplace=True)
			results.sort_values(by=['logp'], inplace=True)

			ci_upper = -1 * np.log10(scipy.beta.ppf(0.95, range(1,len(results[pcol]) + 1), range(len(results[pcol]),0,-1)))
			ci_upper.sort_values(inplace=True)
			ci_lower = -1 * np.log10(scipy.beta.ppf(0.05, range(1,len(results[pcol]) + 1), range(len(results[pcol]),0,-1)))
			ci_lower.sort_values(inplace=True)
			
			ro.globalenv['df'] = ro.DataFrame({'a': ro.FloatVector(a), 'b': ro.FloatVector(results['logp']), 'ci_lower': ro.FloatVector(ci_lower), 'ci_upper': ro.FloatVector(ci_upper)})
			dftext_label = 'lambda %~~% ' + str(l)
			ro.globalenv['dftext'] = ro.DataFrame({'x': ro.r('Inf'), 'y': 0.5, 'lab': dftext_label})

			if cfg['ext'] == 'tiff':
				ggsave = 'ggsave(filename="%s",plot=pp,width=4,height=4,units="in",bg="white",compression="lzw",dpi=300)' % (cfg['out'] + '.' + pcol + '.qq.tiff')
			elif cfg['ext'] == 'eps':
				ggsave = 'ggsave(filename="%s",plot=pp,width=4,height=4,bg="white",horizontal=True)' % (cfg['out'] + '.' + pcol + '.qq.eps')
			else:
				ggsave = 'ggsave(filename="%s",plot=pp,width=4,height=4,bg="white")' % (cfg['out'] + '.' + pcol + '.qq.pdf')
			ro.r("""
				gp<-ggplot(df)
				pp<-gp + 
					aes_string(x='a',y='b') +
					geom_ribbon(aes_string(x='a',ymin='ci_lower',ymax='ci_upper'), data=df, alpha=0.25, fill='black') + 
					geom_point(size=2) +
					geom_abline(intercept=0, slope=1, alpha=0.5) + 
					scale_x_continuous(expression(Expected~~-log[10](italic(p)))) +
					scale_y_continuous(expression(Observed~~-log[10](italic(p)))) +
					theme_bw(base_size = 12) + 
					geom_text(aes_string(x='x', y='y', label='lab'), data = dftext, colour="black", vjust=0, hjust=1, size = 4, parse=TRUE) +
					theme(axis.title.x = element_text(vjust=-0.5,size=14), axis.title.y = element_text(vjust=1,angle=90,size=14), legend.position = 'none', 
						panel.background = element_blank(), panel.border = element_blank(), panel.grid.minor = element_blank(), 
						panel.grid.major = element_blank(), axis.line = element_line(colour="black"), axis.text = element_text(size=12))
				%s
				""" % (ggsave))

			if np.max(results['logp']) > cfg['crop']:
				print "   generating cropped standard qq plot"
				ro.r('df$b[df$b > ' + str(cfg['crop']) + ']<-' + str(cfg['crop']))
				ro.r('df$shape<-0')
				ro.r('df$shape[df$b == ' + str(cfg['crop']) + ']<-1')
				if cfg['ext'] == 'tiff':
					ggsave = 'ggsave(filename="%s",plot=pp,width=4,height=4,units="in",bg="white",compression="lzw",dpi=300)' % (cfg['out'] + '.' + pcol + '.qq.cropped.tiff')
				elif cfg['ext'] == 'eps':
					ggsave = 'ggsave(filename="%s",plot=pp,width=4,height=4,bg="white",horizontal=True)' % (cfg['out'] + '.' + pcol + '.qq.cropped.eps')
				else:
					ggsave = 'ggsave(filename="%s",plot=pp,width=4,height=4,bg="white")' % (cfg['out'] + '.' + pcol + '.qq.cropped.pdf')
				ro.r("""
					gp<-ggplot(df)
					pp<-gp + 
						aes_string(x='a',y='b') +
						geom_ribbon(aes_string(x='a',ymin='ci_lower',ymax='ci_upper'), data=df, alpha=0.25, fill='black') + 
						geom_point(aes(shape=factor(shape)),size=2) +
						geom_abline(intercept=0, slope=1, alpha=0.5) + 
						scale_x_continuous(expression(Expected~~-log[10](italic(p)))) +
						scale_y_continuous(expression(Observed~~-log[10](italic(p)))) +
						theme_bw(base_size = 12) + 
						geom_text(aes_string(x='x', y='y', label='lab'), data = dftext, colour="black", vjust=0, hjust=1, size = 4, parse=TRUE) +
						theme(axis.title.x = element_text(vjust=-0.5,size=14), axis.title.y = element_text(vjust=1,angle=90,size=14), legend.position = 'none', 
							panel.background = element_blank(), panel.border = element_blank(), panel.grid.minor = element_blank(), 
							panel.grid.major = element_blank(), axis.line = element_line(colour="black"), axis.text = element_text(size=12))
					%s
					""" % (ggsave))

		if cfg['mht']:
			print "   generating standard manhattan plot"
			if not cfg['nogc']:
				print "   adjusting p-values for genomic inflation for p-value column " + pcol
				results[pcol]=2 * scipy.norm.cdf(-1 * np.abs(scipy.norm.ppf(0.5*results[pcol]) / math.sqrt(l)))
			else:
				print "   skipping genomic inflation correction for p-value column " + pcol

			print "   calculating genomic positions"
			results.sort_values(by=['#chr','pos'], inplace=True)
			ticks = []
			lastbase = 0
			results['gpos'] = 0
			nchr = len(list(np.unique(results['#chr'].values)))
			chrs = np.unique(results['#chr'].values)
			if cfg['color']:
				colours = ["#08306B","#41AB5D","#000000","#F16913","#3F007D","#EF3B2C","#08519C","#238B45","#252525","#D94801","#54278F","#CB181D","#2171B5","#006D2C","#525252","#A63603","#6A51A3","#A50F15","#4292C6","#00441B","#737373","#7F2704","#807DBA","#67000D"]
			else:
				colours = ["#08589e","#4eb3d3","#08589e","#4eb3d3","#08589e","#4eb3d3","#08589e","#4eb3d3","#08589e","#4eb3d3","#08589e","#4eb3d3","#08589e","#4eb3d3","#08589e","#4eb3d3","#08589e","#4eb3d3","#08589e","#4eb3d3","#08589e","#4eb3d3","#08589e","#4eb3d3"]
			if nchr == 1:
				results['gpos'] = results['pos']
				results['colours'] = "#08589e"
				if results['gpos'].max() - results['gpos'].min() <= 1000:
					ticks = [x for x in range(results['gpos'].min(),results['gpos'].max()) if x % 100 == 0]
				elif results['gpos'].max() - results['gpos'].min() <= 10000:
					ticks = [x for x in range(results['gpos'].min(),results['gpos'].max()) if x % 1000 == 0]
				elif results['gpos'].max() - results['gpos'].min() <= 100000:
					ticks = [x for x in range(results['gpos'].min(),results['gpos'].max()) if x % 10000 == 0]
				elif results['gpos'].max() - results['gpos'].min() <= 200000:
					ticks = [x for x in range(results['gpos'].min(),results['gpos'].max()) if x % 20000 == 0]
				elif results['gpos'].max() - results['gpos'].min() <= 300000:
					ticks = [x for x in range(results['gpos'].min(),results['gpos'].max()) if x % 30000 == 0]
				elif results['gpos'].max() - results['gpos'].min() <= 400000:
					ticks = [x for x in range(results['gpos'].min(),results['gpos'].max()) if x % 40000 == 0]
				elif results['gpos'].max() - results['gpos'].min() <= 500000:
					ticks = [x for x in range(results['gpos'].min(),results['gpos'].max()) if x % 50000 == 0]
				elif results['gpos'].max() - results['gpos'].min() <= 600000:
					ticks = [x for x in range(results['gpos'].min(),results['gpos'].max()) if x % 60000 == 0]
				elif results['gpos'].max() - results['gpos'].min() <= 700000:
					ticks = [x for x in range(results['gpos'].min(),results['gpos'].max()) if x % 70000 == 0]
				elif results['gpos'].max() - results['gpos'].min() <= 800000:
					ticks = [x for x in range(results['gpos'].min(),results['gpos'].max()) if x % 80000 == 0]
				elif results['gpos'].max() - results['gpos'].min() <= 900000:
					ticks = [x for x in range(results['gpos'].min(),results['gpos'].max()) if x % 90000 == 0]
				elif results['gpos'].max() - results['gpos'].min() <= 1000000:
					ticks = [x for x in range(results['gpos'].min(),results['gpos'].max()) if x % 100000 == 0]
				elif results['gpos'].max() - results['gpos'].min() <= 10000000:
					ticks = [x for x in range(results['gpos'].min(),results['gpos'].max()) if x % 1000000 == 0]
				elif results['gpos'].max() - results['gpos'].min() <= 100000000:
					ticks = [x for x in range(results['gpos'].min(),results['gpos'].max()) if x % 10000000 == 0]
				elif results['gpos'].max() - results['gpos'].min() > 100000000:
					ticks = [x for x in range(results['gpos'].min(),results['gpos'].max()) if x % 25000000 == 0]
			else:
				results['colours'] = "#000000"
				for i in range(len(chrs)):
					print "      processed chromosome " + str(int(chrs[i]))
					if i == 0:
						results.loc[results['#chr'] == chrs[i],'gpos'] = results.loc[results['#chr'] == chrs[i],'pos']
					else:
						lastbase = lastbase + results.loc[results['#chr'] == chrs[i-1],'pos'].iget(-1)
						results.loc[results['#chr'] == chrs[i],'gpos'] = (results.loc[results['#chr'] == chrs[i],'pos']) + lastbase
					ticks.append(results.loc[results['#chr'] == chrs[i],'gpos'].iloc[(int(math.floor(len(results.loc[results['#chr'] == chrs[i],'gpos']))/2)) + 1])
					results.loc[results['#chr'] == chrs[i],'colours'] = colours[int(chrs[i])]
			results['logp'] = -1 * np.log10(results[pcol])
			if results.shape[0] >= 1000000:
				sig = 5.4e-8
			else:
				sig = 0.05 / results.shape[0]
			print "   significance level set to " + str(sig)
			chr = results['#chr'][0]
			maxy=int(max(np.ceil(-1 * np.log10(sig)),np.ceil(results['logp'].max())))
			if maxy > 20:
				y_breaks = range(0,maxy,5)
				y_labels = range(0,maxy,5)
			else:
				y_breaks = range(0,maxy)
				y_labels = range(0,maxy)
			ro.globalenv['df'] = ro.DataFrame({'gpos': ro.FloatVector(results['gpos']), 'logp': ro.FloatVector(results['logp']), 'colours': ro.FactorVector(results['colours'])})
			ro.globalenv['ticks'] = ro.FloatVector(ticks)
			ro.globalenv['labels'] = ro.Vector(["{:,}".format(x/1000) for x in ticks])
			ro.globalenv['colours'] = ro.StrVector(colours)
			ro.globalenv['chrs'] = ro.FloatVector(chrs)

			print "   generating manhattan plot"
			if cfg['ext'] == 'tiff':
				ggsave = 'ggsave(filename="%s",plot=gp,width=12,height=4,units="in",bg="white",compression="lzw",dpi=300)' % (cfg['out'] + '.' + pcol + '.mht.tiff')
			elif cfg['ext'] == 'eps':
				ggsave = 'ggsave(filename="%s",plot=gp,width=12,height=4,bg="white",horizontal=True)' % (cfg['out'] + '.' + pcol + '.mht.eps')
			else:
				ggsave = 'ggsave(filename="%s",plot=gp,width=12,height=4,bg="white")' % (cfg['out'] + '.' + pcol + '.mht.pdf')
			if nchr == 1:
				ro.r("""
					gp<-ggplot(df, aes_string(x='gpos',y='logp')) +
						geom_hline(yintercept = -1 * log10(%g),colour="#B8860B", linetype=5, size = 0.25) + 
						geom_point(size=1.5) + 
						scale_x_continuous(expression(Chromosome~~%d~~(kb))'),breaks=ticks,labels=labels) + \
						scale_y_continuous(expression(-log[10](italic(p))),limits=c(0,%d)) + \
						theme_bw(base_size = 8) + \
						theme(axis.title.x = element_text(vjust=-0.5,size=14), axis.title.y = element_text(vjust=1,angle=90,size=14), 
								panel.background = element_blank(), panel.border = element_blank(), panel.grid.minor = element_blank(), 
								panel.grid.major = element_blank(), axis.line = element_line(colour="black"), axis.title = element_text(size=10), 
								axis.text = element_text(size=8), legend.position = 'none', axis.text = element_text(size=12))
					%s
					""" % (sig, chr, maxy, ggsave))
			else:
				ro.r("""
					gp = ggplot(df, aes_string(x='gpos',y='logp',colour='colours')) + 
						geom_hline(yintercept = -1 * log10(%g),colour="#B8860B", linetype=5, size = 0.25) + 
						geom_point(size=1.5) + 
						scale_colour_manual(values=colours) + 
						scale_x_continuous(expression(Chromosome),breaks=ticks,labels=chrs) + 
						scale_y_continuous(expression(-log[10](italic(p))),limits=c(0,%d)) + 
						theme_bw(base_size = 8) + 
						theme(axis.title.x = element_text(vjust=-0.5,size=14), axis.title.y = element_text(vjust=1,angle=90,size=14), 
								panel.background = element_blank(), panel.border = element_blank(), panel.grid.minor = element_blank(), 
								panel.grid.major = element_blank(), axis.line = element_line(colour="black"), axis.title = element_text(size=8), 
								axis.text = element_text(size=6), legend.position = 'none', axis.text = element_text(size=12))
					%s
					""" % (sig, maxy, ggsave))

			if maxy > cfg['crop']:
				maxy = cfg['crop']
				ro.r('df$logp[df$logp > ' + str(cfg['crop']) + ']<-' + str(cfg['crop']))
				ro.r('df$shape<-0')
				ro.r('df$shape[df$logp == ' + str(cfg['crop']) + ']<-1')
				print "   generating cropped manhattan plot"
				if cfg['ext'] == 'tiff':
					ggsave = 'ggsave(filename="%s",plot=gp,width=12,height=4,units="in",bg="white",compression="lzw",dpi=300)' % (cfg['out'] + '.' + pcol + '.mht.cropped.tiff')
				elif cfg['ext'] == 'eps':
					ggsave = 'ggsave(filename="%s",plot=gp,width=12,height=4,bg="white",horizontal=True)' % (cfg['out'] + '.' + pcol + '.mht.cropped.eps')
				else:
					ggsave = 'ggsave(filename="%s",plot=gp,width=12,height=4,bg="white")' % (cfg['out'] + '.' + pcol + '.mht.cropped.pdf')
				if nchr == 1:
					ro.r("""
						gp<-ggplot(df, aes_string(x='gpos',y='logp')) +
							geom_hline(yintercept = -1 * log10(%g),colour="#B8860B", linetype=5, size = 0.25) + 
							geom_point(aes(shape=factor(shape)),size=1.5) + 
							scale_x_continuous(expression(Chromosome~~%d~~(kb))'),breaks=ticks,labels=labels) + 
							scale_y_continuous(expression(-log[10](italic(p))),limits=c(0,%d)) + 
							theme_bw(base_size = 8) + 
							theme(axis.title.x = element_text(vjust=-0.5,size=14), axis.title.y = element_text(vjust=1,angle=90,size=14), 
									panel.background = element_blank(), panel.border = element_blank(), panel.grid.minor = element_blank(), 
									panel.grid.major = element_blank(), axis.line = element_line(colour="black"), axis.title = element_text(size=10), 
									axis.text = element_text(size=8), legend.position = 'none', axis.text = element_text(size=12))
						%s
						""" % (sig, chr, maxy, ggsave))
				else:
					ro.r("""
						gp = ggplot(df, aes_string(x='gpos',y='logp',colour='colours')) + 
							geom_hline(yintercept = -1 * log10(%g),colour="#B8860B", linetype=5, size = 0.25) + 
							geom_point(aes(shape=factor(shape)),size=1.5) + 
							scale_colour_manual(values=colours) + 
							scale_x_continuous(expression(Chromosome),breaks=ticks,labels=chrs) + 
							scale_y_continuous(expression(-log[10](italic(p))),limits=c(0,%d)) + 
							theme_bw(base_size = 8) + 
							theme(axis.title.x = element_text(vjust=-0.5,size=14), axis.title.y = element_text(vjust=1,angle=90,size=14), 
									panel.background = element_blank(), panel.border = element_blank(), panel.grid.minor = element_blank(), 
									panel.grid.major = element_blank(), axis.line = element_line(colour="black"), axis.title = element_text(size=8), 
									axis.text = element_text(size=6), legend.position = 'none', axis.text = element_text(size=12))
						%s
						""" % (sig, maxy, ggsave))

	print "process complete"
	return 0
