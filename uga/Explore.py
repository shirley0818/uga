import pandas as pd
import numpy as np
import subprocess
import math
import tabix
from SystemFxns import Error
from FileFxns import Coordinates
import scipy.stats as scipy
import rpy2.robjects as ro
from rpy2.robjects.packages import importr
import re
import os
from Bio import bgzf

pd.options.mode.chained_assignment = None

#from memory_profiler import profile, memory_usage
#@profile
def Explore(data, 
			out, 
			qq = False, 
			qq_n = False, 
			mht = False, 
			color = False, 
			ext = 'tiff', 
			sig = 0.000000054, 
			gc = False, 
			set_gc = None, 
			stat = 'marker', 
			regional_n = None, 
			region = None, 
			region_id = None, 
			region_list = None, 
			tag = None, 
			unrel = False, 
			f_dist_dfn = None, 
			f_dist_dfd = None, 
			lz_source = None, 
			lz_build = None, 
			lz_pop = None, 
			callrate_thresh = None, 
			rsq_thresh = None, 
			freq_thresh = None, 
			hwe_thresh = None, 
			effect_thresh = None, 
			stderr_thresh = None, 
			or_thresh = None, 
			df_thresh = None):

	print "explore options ..."
	for arg in locals().keys():
		if not locals()[arg] in [None, False]:
			print "   {0:>{1}}".format(str(arg), len(max(locals().keys(),key=len))) + ": " + str(locals()[arg])

	if qq or mht:
		import rpy2.robjects.lib.ggplot2 as ggplot2
		rgrid = importr('grid')
		grdevices = importr('grDevices')

	fcols = ['#chr','pos','a1','a2','marker','callrate','freq']
	fcols.append('freq.unrel')
	fcols.append('rsq')
	fcols.append('rsq.unrel')
	fcols.append('hwe')
	fcols.append('hwe.unrel')
	fcols.append('samples')
	fcols.append('n')
	fcols.append(stat + '.effect')
	fcols.append(stat + '.stderr')
	fcols.append(stat + '.or')
	fcols.append(stat + '.z')
	fcols.append(stat + '.p')
	fcols.append(stat + '.dir')
	chr = '#chr'
	pos = 'pos'
	rsq = 'rsq.unrel' if unrel else 'rsq'
	freq = 'freq.unrel' if unrel else 'freq'
	hwe = 'hwe.unrel' if unrel else 'hwe'
	effect = stat + '.effect'
	stderr = stat + '.stderr'
	oddsratio = stat + '.or'
	z = stat + '.z'
	p = stat + '.p'
	meta_dir = stat + '.dir'
	if tag is not None:
		fcols = [tag + '.' + x if x not in ['#chr','pos','a1','a2'] else x for x in fcols]
		rsq = tag + '.' + rsq
		freq = tag + '.' + freq
		hwe = tag + '.' + hwe
		effect = tag + '.' + effect
		stderr = tag + '.' + stderr
		oddsratio = tag + '.' + oddsratio
		z = tag + '.' + z
		p = tag + '.' + p
		meta_dir = tag + '.' + meta_dir

	##### GENERATE REGION LIST #####
	regions = None
	if not region_list is None:
		print "loading region list"
		marker_list = Coordinates(region_list).Load()
		regions = list(marker_list['region'])
	elif not region is None:
		if len(region.split(':')) > 1:
			marker_list = pd.DataFrame({'chr': [re.split(':|-',region)[0]],'start': [re.split(':|-',region)[1]],'end': [re.split(':|-',region)[2]],'region': [region]})
		else:
			marker_list = pd.DataFrame({'chr': [region],'start': ['NA'],'end': ['NA'],'region': [region]})
		marker_list['reg_id'] = region_id if not region_id is None else 'NA'
		regions = list(marker_list['region'])

	##### read data from file #####
	print "loading results from file"
	if regions is None:
		reader = pd.read_table(data, sep='\t', chunksize=1000000,compression='gzip',dtype=object)
		i = 0
		for chunk in reader:
			i = i+1
			chunk = chunk[[x for x in chunk.columns if x in fcols]]
			lines = len(chunk)
			chunk = chunk[pd.notnull(chunk[p])]
			chunk = chunk[chunk[p] != 0]
			if len(chunk) > 0:
				if i == 1:
					pvals = chunk
				else:
					pvals = pvals.append(chunk)
			print "   processed " + str((i-1)*1000000 + lines) + " lines: " + str(len(chunk)) + " markers added: " + str(len(pvals.index)) + " total"
		pvals.columns = [a.replace('#','') for a in pvals.columns]
		chr = 'chr'
	else:
		try:
			h = subprocess.Popen(['tabix','-h',data,'0'], stdout=subprocess.PIPE)
		except:
			usage(Error("process_file " + data + " has incorrect format"))
		header = h.communicate()[0]
		header = header.replace("#","")
		header = header.strip()
		header = header.split()		
		reader = tabix.open(data)
		for r in range(len(marker_list.index)):
			reg = marker_list['region'][r]
			try:
				records = reader.querys(reg)
			except:
				pass
			else:
				chunk = pd.DataFrame([record for record in records])
				chunk.columns = header
				chunk = chunk[chunk[p] != 'NA']
				chunk = chunk[pd.notnull(chunk[p])]
				chunk = chunk[chunk[p] != 0]
				if len(chunk) > 0:
					if r == 0:
						pvals = chunk
					else:
						pvals = pvals.append(chunk)
			print "   processed region " + str(r+1) + "/" + str(len(marker_list.index)) + " (" + str(marker_list['reg_id'][r]) + " " + str(marker_list['region'][r]) + "): " + str(len(chunk)) + " markers added: " + str(len(pvals.index)) + " total"
		pvals[pvals == 'NA'] = float('nan')
	pvals[[x for x in pvals.columns if 'rsq' in x or 'hwe' in x or 'freq' in x or '.effect' in x or '.stderr' in x or '.or' in x or '.z' in x or '.p' in x]] = pvals[[x for x in pvals.columns if 'rsq' in x or 'hwe' in x or 'freq' in x or '.effect' in x or '.stderr' in x or '.or' in x or '.z' in x or '.p' in x]].astype(float)
	pvals[['chr','pos']] = pvals[['chr','pos']].astype(int)

	##### filter data #####
	if rsq_thresh:
		print "filtering data for imputation quality"
		pvals = pvals[(pvals[rsq] >= rsq_thresh) & (pvals[rsq] <= 1/rsq_thresh)]
	if freq_thresh:
		print "filtering data for frequency"
		pvals = pvals[(pvals[freq] >= freq_thresh) & (pvals[freq] <= 1 - freq_thresh)]
	if hwe_thresh:
		print "filtering data for Hardy Weinberg p-value"
		pvals = pvals[pvals[hwe] > hwe_thresh]
	if callrate_thresh:
		print "filtering data for callrate"
		pvals = pvals[pvals[callrate] >= callrate_thresh]
	if effect_thresh:
		print "filtering data for effect estimate"
		pvals = pvals[(pvals[effect] <= effect_thresh) & (pvals[effect] >= -1 * effect_thresh)]
	if stderr_thresh:
		print "filtering data for standard error"
		pvals = pvals[pvals[stderr] <= stderr_thresh]
	if or_thresh:
		print "filtering data for odds ratio"
		pvals = pvals[(pvals[oddsratio] <= or_thresh) & (pvals[oddsratio] >= 1 / or_thresh)]
	def count_df(x):
		return len(re.findall('\\+|-',x))
	if df_thresh:
		print "filtering data for degrees of freedom"
		pvals = pvals[pvals[meta_dir].apply(count_df) >= int(df_thresh) + 1]
	print str(len(pvals)) + " markers left after filtering"
	
	##### calculate p-value for f-distribution #####
	if regions is None:
		if not f_dist_dfn is None:
			print "calculating new p-values for f-distribution"
			pvals[p + '_orig']=pvals[p]
			out = out + '.fdist'
			pvals[p]=1-scipy.f.cdf(pvals[z] ** 2,dfn=int(f_dist_dfn),dfd=int(f_dist_dfd))

		l=np.median(scipy.chi2.ppf([1-x for x in pvals[p].tolist()], df=1))/scipy.chi2.ppf(0.5,1)
		print "genomic inflation (all markers) = " + str(l)
		if freq in pvals:
			lA='NA'
			lB='NA'
			lC='NA'
			lD='NA'
			lE='NA'
			lE_n=len(pvals[p][(pvals[freq] < 0.01) | (pvals[freq] > 0.99)])
			lD_n=len(pvals[p][((pvals[freq] >= 0.01) & (pvals[freq] < 0.03)) | ((pvals[freq] <= 0.99) & (pvals[freq] > 0.97))])
			lC_n=len(pvals[p][((pvals[freq] >= 0.03) & (pvals[freq] < 0.05)) | ((pvals[freq] <= 0.97) & (pvals[freq] > 0.95))])
			lB_n=len(pvals[p][((pvals[freq] >= 0.05) & (pvals[freq] < 0.1)) | ((pvals[freq] <= 0.95) & (pvals[freq] > 0.9))])
			lA_n=len(pvals[p][(pvals[freq] >= 0.1) & (pvals[freq] <= 0.9)])
			if lE_n > 0:
				lE=np.median(scipy.chi2.ppf([1-x for x in pvals[p][(pvals[freq] < 0.01) | (pvals[freq] > 0.99)].tolist()], df=1))/scipy.chi2.ppf(0.5,1)
			if lD_n > 0:
				lD=np.median(scipy.chi2.ppf([1-x for x in pvals[p][((pvals[freq] >= 0.01) & (pvals[freq] < 0.03)) | ((pvals[freq] <= 0.99) & (pvals[freq] > 0.97))].tolist()], df=1))/scipy.chi2.ppf(0.5,1)
			if lC_n > 0:
				lC=np.median(scipy.chi2.ppf([1-x for x in pvals[p][((pvals[freq] >= 0.03) & (pvals[freq] < 0.05)) | ((pvals[freq] <= 0.97) & (pvals[freq] > 0.95))].tolist()], df=1))/scipy.chi2.ppf(0.5,1)
			if lB_n > 0:
				lB=np.median(scipy.chi2.ppf([1-x for x in pvals[p][((pvals[freq] >= 0.05) & (pvals[freq] < 0.1)) | ((pvals[freq] <= 0.95) & (pvals[freq] > 0.9))].tolist()], df=1))/scipy.chi2.ppf(0.5,1)
			if lA_n > 0:
				lA=np.median(scipy.chi2.ppf([1-x for x in pvals[p][(pvals[freq] >= 0.1) & (pvals[freq] <= 0.9)].tolist()], df=1))/scipy.chi2.ppf(0.5,1)
			print "genomic inflation (MAF >= 10%, n=" + str(lA_n) + ") = " + str(lA)
			print "genomic inflation (5% <= MAF < 10%, n=" + str(lB_n) + ") = " + str(lB)
			print "genomic inflation (3% <= MAF < 5%, n=" + str(lC_n) + ") = " + str(lC)
			print "genomic inflation (1% <= MAF < 3%, n=" + str(lD_n) + ") = " + str(lD)
			print "genomic inflation (MAF < 1%, n=" + str(lE_n) + ") = " + str(lE)

		if qq and freq in pvals:
			a = -1 * np.log10(ro.r('ppoints(' + str(len(pvals.index)) + ')'))
			a.sort()
			
			pvals['logp'] = -1 * np.log10(pvals[p])
			pvals.sort(columns=['logp'], inplace=True)
			pvals['MAF'] = 'E'
			pvals['MAF'][(pvals[freq] >= 0.01) & (pvals[freq] <= 0.99)] = 'D'
			pvals['MAF'][(pvals[freq] >= 0.03) & (pvals[freq] <= 0.97)] = 'C'
			pvals['MAF'][(pvals[freq] >= 0.05) & (pvals[freq] <= 0.95)] = 'B'
			pvals['MAF'][(pvals[freq] >= 0.1) & (pvals[freq] <= 0.9)] = 'A'

			ci_upper = -1 * np.log10(scipy.beta.ppf(0.95, range(1,len(pvals[p]) + 1), range(len(pvals[p]),0,-1)))
			ci_upper.sort()
			ci_lower = -1 * np.log10(scipy.beta.ppf(0.05, range(1,len(pvals[p]) + 1), range(len(pvals[p]),0,-1)))
			ci_lower.sort()

			df = ro.DataFrame({'a': ro.FloatVector(a), 'b': ro.FloatVector(pvals['logp']), 'MAF': ro.StrVector(pvals['MAF']), 'ci_upper': ro.FloatVector(ci_upper), 'ci_lower': ro.FloatVector(ci_lower)})
			dftext_label = 'lambda %~~% ' + str(round(l,3))
			dftext = ro.DataFrame({'x': ro.r('Inf'), 'y': 0.5, 'lab': dftext_label})

			print "generating qq plot"
			if ext == 'tiff':
				grdevices.tiff(out + '.qq.' + ext,width=4,height=4,units="in",bg="white",compression="lzw",res=300)
			elif ext == 'eps':
				grdevices.postscript(out + '.qq.' + ext,width=4,height=4,bg="white",horizontal=False)
			else:
				grdevices.pdf(out + '.qq.' + ext,width=4,height=4,bg="white")
			gp = ggplot2.ggplot(df)
			pp = gp + \
					ggplot2.aes_string(x='a',y='b') + \
					ggplot2.geom_ribbon(ggplot2.aes_string(x='a',ymin='ci_lower',ymax='ci_upper'), data=df, alpha=0.15, fill='black') + \
					ggplot2.geom_point(ggplot2.aes_string(color='MAF'), size=2) + \
					ggplot2.scale_colour_manual(values=ro.r('c("E"="#a8ddb5", "D"="#7bccc4", "C"="#4eb3d3", "B"="#2b8cbe", "A"="#08589e")'), labels=ro.r('c("E"="MAF < 1%","D"="1% <= MAF < 3%","C"="3% <= MAF < 5%","B"="5% <= MAF < 10%","A"="MAF >= 10%")')) + \
					ggplot2.geom_abline(intercept=0, slope=1, alpha=0.5) + \
					ggplot2.scale_x_continuous(ro.r('expression(Expected~~-log[10](italic(p)))')) + \
					ggplot2.scale_y_continuous(ro.r('expression(Observed~~-log[10](italic(p)))')) + \
					ggplot2.theme_bw(base_size = 12) + \
					ggplot2.geom_text(ggplot2.aes_string(x='x', y='y', label='lab'), data = dftext, colour="black", vjust=0, hjust=1, size = 4, parse=ro.r('TRUE'))
			if qq_n:
				dftext2_label = '~~~ n == ' + str(len(pvals))
				dftext2 = ro.DataFrame({'x': ro.r('Inf'), 'y': 0, 'lab': dftext2_label})
				pp = pp + ggplot2.geom_text(ggplot2.aes_string(x='x', y='y', label='lab'), data = dftext2, colour="black", vjust=0, hjust=1, size = 4, parse=ro.r('TRUE'))
			pp = pp + ggplot2.theme(**{'axis.title.x': ggplot2.element_text(vjust=-0.5,size=14), 'axis.title.y': ggplot2.element_text(vjust=1,angle=90,size=14), 'legend.title': ggplot2.element_blank(), 'legend.key.height': ro.r.unit(0.1,"in"), 'legend.text': ggplot2.element_text(size=5), 'legend.key': ggplot2.element_blank(), 'legend.justification': ro.r('c(0,1)'), 'legend.position': ro.r('c(0,1)'), 'panel.background': ggplot2.element_blank(), 'panel.border': ggplot2.element_blank(), 'panel.grid.minor': ggplot2.element_blank(), 'panel.grid.major': ggplot2.element_blank(), 'axis.line': ro.r('element_line(colour="black")'), 'axis.text': ggplot2.element_text(size=12)})
			pp.plot()
			grdevices.dev_off()
		elif qq:
			a = -1 * np.log10(ro.r('ppoints(' + str(len(pvals.index)) + ')'))
			a.sort()
			
			pvals['logp'] = -1 * np.log10(pvals[p]) + 0.0
			pvals.sort(columns=['logp'], inplace=True)
			
			ci_upper = -1 * np.log10(scipy.beta.ppf(0.95, range(1,len(pvals[p]) + 1), range(len(pvals[p]),0,-1)))
			ci_upper.sort()
			ci_lower = -1 * np.log10(scipy.beta.ppf(0.05, range(1,len(pvals[p]) + 1), range(len(pvals[p]),0,-1)))
			ci_lower.sort()

			df = ro.DataFrame({'a': ro.FloatVector(a), 'b': ro.FloatVector(pvals['logp']), 'ci_upper': ro.FloatVector(ci_upper), 'ci_lower': ro.FloatVector(ci_lower)})
			dftext_label = 'lambda %~~% ' + str(round(l,3))
			dftext = ro.DataFrame({'x': ro.r('Inf'), 'y': 0.5, 'lab': dftext_label})

			print "generating qq plot"
			if ext == 'tiff':
				grdevices.tiff(out + '.qq.' + ext,width=4,height=4,units="in",bg="white",compression="lzw",res=300)
			elif ext == 'eps':
				grdevices.postscript(out + '.qq.' + ext,width=4,height=4,bg="white",horizontal=False)
			else:
				grdevices.pdf(out + '.qq.' + ext,width=4,height=4,bg="white")
			gp = ggplot2.ggplot(df)
			pp = gp + \
					ggplot2.aes_string(x='a',y='b') + \
					ggplot2.geom_ribbon(ggplot2.aes_string(x='a',ymin='ci_lower',ymax='ci_upper'), data=df, alpha=0.15, fill='black') + \
					ggplot2.geom_point(size=2) + \
					ggplot2.geom_abline(intercept=0, slope=1, alpha=0.5) + \
					ggplot2.scale_x_continuous(ro.r('expression(Expected~~-log[10](italic(p)))')) + \
					ggplot2.scale_y_continuous(ro.r('expression(Observed~~-log[10](italic(p)))')) + \
					ggplot2.theme_bw(base_size = 12) + \
					ggplot2.geom_text(ggplot2.aes_string(x='x', y='y', label='lab'), data = dftext, colour="black", vjust=0, hjust=1, size = 4, parse=ro.r('TRUE'))
			if qq_n:
				dftext2_label = '~~~ n == ' + str(len(pvals))
				dftext2 = ro.DataFrame({'x': ro.r('Inf'), 'y': 0, 'lab': dftext2_label})
				pp = pp + ggplot2.geom_text(ggplot2.aes_string(x='x', y='y', label='lab'), data = dftext2, colour="black", vjust=0, hjust=1, size = 4, parse=ro.r('TRUE'))
			pp = pp + ggplot2.theme(**{'axis.title.x': ggplot2.element_text(vjust=-0.5,size=14), 'axis.title.y': ggplot2.element_text(vjust=1,angle=90,size=14), 'legend.position': 'none', 'panel.background': ggplot2.element_blank(), 'panel.border': ggplot2.element_blank(), 'panel.grid.minor': ggplot2.element_blank(), 'panel.grid.major': ggplot2.element_blank(), 'axis.line': ro.r('element_line(colour="black")'), 'axis.text': ggplot2.element_text(size=12)})
			pp.plot()
			grdevices.dev_off()
		
		if gc:
			print "adjusting p-values for genomic inflation"
			pvals[p]=2 * scipy.norm.cdf(-1 * np.abs(scipy.norm.ppf(0.5*pvals[p]) / math.sqrt(l)))

		if mht:
			print "calculating genomic positions for manhattan plot"
			df = pvals[[chr,pos,p]].reset_index(drop=True)
			df.sort(columns=[chr,pos], inplace=True)
			ticks = []
			lastbase = 0
			df['gpos'] = 0
			nchr = len(list(np.unique(df[chr].values)))
			chrs = np.unique(df[chr].values)
			if color:
				colours = ["#08306B","#41AB5D","#000000","#F16913","#3F007D","#EF3B2C","#08519C","#238B45","#252525","#D94801","#54278F","#CB181D","#2171B5","#006D2C","#525252","#A63603","#6A51A3","#A50F15","#4292C6","#00441B","#737373","#7F2704","#807DBA","#67000D"]
			else:
				colours = ["#000000","#696969","#000000","#696969","#000000","#696969","#000000","#696969","#000000","#696969","#000000","#696969","#000000","#696969","#000000","#696969","#000000","#696969","#000000","#696969","#000000","#696969","#000000","#696969"]
			if nchr == 1:
				df['gpos'] = df[pos]
				df['colours'] = "#000000"
				if df['gpos'].max() - df['gpos'].min() <= 1000:
					ticks = [x for x in range(df['gpos'].min(),df['gpos'].max()) if x % 100 == 0]
				elif df['gpos'].max() - df['gpos'].min() <= 10000:
					ticks = [x for x in range(df['gpos'].min(),df['gpos'].max()) if x % 1000 == 0]
				elif df['gpos'].max() - df['gpos'].min() <= 100000:
					ticks = [x for x in range(df['gpos'].min(),df['gpos'].max()) if x % 10000 == 0]
				elif df['gpos'].max() - df['gpos'].min() <= 200000:
					ticks = [x for x in range(df['gpos'].min(),df['gpos'].max()) if x % 20000 == 0]
				elif df['gpos'].max() - df['gpos'].min() <= 300000:
					ticks = [x for x in range(df['gpos'].min(),df['gpos'].max()) if x % 30000 == 0]
				elif df['gpos'].max() - df['gpos'].min() <= 400000:
					ticks = [x for x in range(df['gpos'].min(),df['gpos'].max()) if x % 40000 == 0]
				elif df['gpos'].max() - df['gpos'].min() <= 500000:
					ticks = [x for x in range(df['gpos'].min(),df['gpos'].max()) if x % 50000 == 0]
				elif df['gpos'].max() - df['gpos'].min() <= 600000:
					ticks = [x for x in range(df['gpos'].min(),df['gpos'].max()) if x % 60000 == 0]
				elif df['gpos'].max() - df['gpos'].min() <= 700000:
					ticks = [x for x in range(df['gpos'].min(),df['gpos'].max()) if x % 70000 == 0]
				elif df['gpos'].max() - df['gpos'].min() <= 800000:
					ticks = [x for x in range(df['gpos'].min(),df['gpos'].max()) if x % 80000 == 0]
				elif df['gpos'].max() - df['gpos'].min() <= 900000:
					ticks = [x for x in range(df['gpos'].min(),df['gpos'].max()) if x % 90000 == 0]
				elif df['gpos'].max() - df['gpos'].min() <= 1000000:
					ticks = [x for x in range(df['gpos'].min(),df['gpos'].max()) if x % 100000 == 0]
				elif df['gpos'].max() - df['gpos'].min() <= 10000000:
					ticks = [x for x in range(df['gpos'].min(),df['gpos'].max()) if x % 1000000 == 0]
				elif df['gpos'].max() - df['gpos'].min() <= 100000000:
					ticks = [x for x in range(df['gpos'].min(),df['gpos'].max()) if x % 10000000 == 0]
				elif df['gpos'].max() - df['gpos'].min() > 100000000:
					ticks = [x for x in range(df['gpos'].min(),df['gpos'].max()) if x % 25000000 == 0]
			else:
				df['colours'] = "#000000"
				for i in range(len(chrs)):
					print "   processed chromosome " + str(int(chrs[i]))
					if i == 0:
						df['gpos'][df[chr] == chrs[i]] = df[pos][df[chr] == chrs[i]]
					else:
						lastbase = lastbase + df[pos][df[chr] == chrs[i-1]].iget(-1)
						df['gpos'][df[chr] == chrs[i]] = (df[pos][df[chr] == chrs[i]]) + lastbase
					ticks.append(df['gpos'][df[chr] == chrs[i]].iloc[(int(math.floor(len(df['gpos'][df[chr] == chrs[i]]))/2)) + 1])
					df['colours'][df[chr] == chrs[i]] = colours[int(chrs[i])]
			df['logp'] = -1 * np.log10(df[p])
			maxy=int(max(np.ceil(-1 * np.log10(sig)),np.ceil(df['logp'].max())))
			if maxy > 20:
				y_breaks = range(0,maxy,5)
				y_labels = range(0,maxy,5)
			else:
				y_breaks = range(0,maxy)
				y_labels = range(0,maxy)
			rdf = ro.DataFrame({'gpos': ro.FloatVector(df['gpos']), 'logp': ro.FloatVector(df['logp']), 'colours': ro.FactorVector(df['colours'])})
			if ext == 'tiff':
				grdevices.tiff(out + '.mht.' + ext,width=12,height=4,units="in",bg="white",compression="lzw",res=300)
			elif ext == 'eps':
				grdevices.postscript(out + '.mht.' + ext,width=12,height=4,bg="white",horizontal=False)
			else:
				grdevices.pdf(out + '.mht.' + ext,width=12,height=4,bg="white")
			print "generating manhattan plot"
			if nchr == 1:
				gp = ggplot2.ggplot(rdf)
				pp = gp + \
						ggplot2.aes_string(x='gpos',y='logp') + \
						ggplot2.geom_hline(yintercept = -1 * np.log10(sig),colour="#B8860B", linetype=5, size = 0.25) + \
						ggplot2.geom_point(size=1.5) + \
						ggplot2.scale_x_continuous(ro.r('expression(Chromosome~~' + str(df[chr][0]) + '~~(kb))'),breaks=ro.FloatVector(ticks),labels=ro.Vector(["{:,}".format(x/1000) for x in ticks])) + \
						ggplot2.scale_y_continuous(ro.r('expression(-log[10](italic(p)))'),limits=ro.r('c(0,' + str(maxy) + ')')) + \
						ggplot2.theme_bw(base_size = 8) + \
						ggplot2.theme(**{'axis.title.x': ggplot2.element_text(vjust=-0.5,size=14), 'axis.title.y': ggplot2.element_text(vjust=1,angle=90,size=14), 'panel.background': ggplot2.element_blank(), 'panel.border': ggplot2.element_blank(), 'panel.grid.minor': ggplot2.element_blank(), 'panel.grid.major': ggplot2.element_blank(), 'axis.line': ro.r('element_line(colour="black")'), 'axis.title': ggplot2.element_text(size=10), 'axis.text': ggplot2.element_text(size=8), 'legend.position': 'none', 'axis.text': ggplot2.element_text(size=12)})
				pp.plot()
			else:
				gp = ggplot2.ggplot(rdf)
				pp = gp + \
						ggplot2.aes_string(x='gpos',y='logp',colour='colours') + \
						ggplot2.geom_hline(yintercept = -1 * np.log10(sig),colour="#B8860B", linetype=5, size = 0.25) + \
						ggplot2.geom_point(size=1.5) + \
						ggplot2.scale_colour_manual(values=ro.StrVector(colours)) + \
						ggplot2.scale_x_continuous(ro.r('expression(Chromosome)'),breaks=ro.FloatVector(ticks),labels=ro.FloatVector(chrs)) + \
						ggplot2.scale_y_continuous(ro.r('expression(-log[10](italic(p)))'),limits=ro.r('c(0,' + str(maxy) + ')')) + \
						ggplot2.theme_bw(base_size = 8) + \
						ggplot2.theme(**{'axis.title.x': ggplot2.element_text(vjust=-0.5,size=14), 'axis.title.y': ggplot2.element_text(vjust=1,angle=90,size=14), 'panel.background': ggplot2.element_blank(), 'panel.border': ggplot2.element_blank(), 'panel.grid.minor': ggplot2.element_blank(), 'panel.grid.major': ggplot2.element_blank(), 'axis.line': ro.r('element_line(colour="black")'), 'axis.title': ggplot2.element_text(size=8), 'axis.text': ggplot2.element_text(size=6), 'legend.position': 'none', 'axis.text': ggplot2.element_text(size=12)})
				pp.plot()
			grdevices.dev_off()

		##### DETERMINE TOP REGIONS #####
		regions = []
		pvals_top = pvals.copy()
		if regional_n is not None:
			print "determining top regions for regional manhattan plots"
			pvals_top.sort(columns=[p], inplace=True)
			while len(regions) < regional_n:
				region_temp = str(pvals_top['chr'].iloc[0]) + ':' + str(pvals_top['pos'].iloc[0] - 100000) + '-' + str(pvals_top['pos'].iloc[0] + 100000)
				regions.append(region_temp)
				pvals_top = pvals_top[~((pvals_top['chr'] == int(region_temp.split(':')[0])) & (pvals_top['pos'] >= int(region_temp.split(':')[1].split('-')[0])) & (pvals_top['pos'] <= int(region_temp.split(':')[1].split('-')[1])))]
	else:
		if set_gc is not None:
			print "adjusting p-values for genomic inflation"
			pvals[p]=2 * scipy.norm.cdf(-1 * np.abs(scipy.norm.ppf(0.5*pvals[p]) / math.sqrt(set_gc)))

	if len(regions) > 0:
		print "generating regional plots"
		home_dir = os.path.expanduser("~")
		for reg in regions:
			chr = int(reg.split(':')[0])
			start = int(reg.split(':')[1].split('-')[0])
			end = int(reg.split(':')[1].split('-')[1])
			pvals_region = pvals[(pvals['chr'] == chr) & (pvals['pos'] >= start) & (pvals['pos'] <= end)]
			pvals_region['MarkerName'] = pvals_region['marker'].values
			pvals_region['MarkerName'] = pvals_region['MarkerName'].map(lambda x: x.split(':')[0] + ':' + x.split(':')[1] if not 'rs' in x else x)
			pvals_region['P-value'] = pvals_region[p].values
			pvals_region.sort(columns=['P-value'], inplace=True)
			pvals_region = pvals_region[['MarkerName','P-value','pos']]
			pvals_region.to_csv(out + '.rgnl.chr' + reg.replace(':','bp') + '.plotdata',header=True, index=False, sep='\t')
			cmd = home_dir + '/locuszoom --metal ' + out + '.rgnl.chr' + reg.replace(':','bp') + '.plotdata --chr ' + str(chr) + ' --start ' + str(start) + ' --end ' + str(end) + ' --plotonly --cache None --prefix ' + out
			if lz_pop is not None:
				cmd = cmd + ' --source ' + lz_source + ' --build ' + lz_build + ' --pop ' + lz_pop 
			else:
				cmd = cmd + ' --no-ld'
			try:
				pr = subprocess.Popen(cmd,shell=True)
				pr.wait()
			except KeyboardInterrupt:
				kill_all(pr.pid)
				print Highlight("process terminated by user")
				sys.exit(1)
			print "   regional plot " + reg + " finished"

	print "process complete"
