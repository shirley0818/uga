import os
import sys
import getopt
import subprocess
import gzip
import tabix
import math
import numpy as np
import pandas as pd
pd.options.mode.chained_assignment = None
from rpy2.robjects.packages import importr
import pandas.rpy.common as py2r
import re
from itertools import islice
from Bio import bgzf
import psutil
from MarkerCalc import *
from Messages import Error
from Stats import *
from Coordinates import *

def Model(out = None, 
			data = None, 
			samples = None, 
			pheno = None, 
			model = None, 
			fid = None, 
			iid = None, 
			method = None, 
			focus = None, 
			sig = 5, 
			region_list = None, 
			region = None, 
			sex = None, 
			male = None, 
			female = None, 
			buffer = 100, 
			miss = None, 
			freq = None, 
			rsq = None, 
			hwe = None, 
			case = 1, 
			ctrl = 0, 
			format = 'oxford', 
			mem = 3, 
			nofail = False):
	
	print "   ... arguments"
	for arg in locals().keys():
		if not locals()[arg] in [None, False]:
			print "      {0:>{1}}".format(str(arg), len(max(locals().keys(),key=len))) + ": " + str(locals()[arg])

	assert out, Error("an output file must be specified")
	assert data, Error("a data file must be specified")
	assert samples, Error("a sample file must be specified")
	assert pheno, Error("a phenotype file must be specified")
	assert model, Error("a model must be specified")
	assert fid, Error("a family ID column must be specified")
	assert iid, Error("an individual ID column must be specified")
	assert method, Error("an analysis method must be specified")
	
	fxn = method.split('_')[1] if method in ["gee_gaussian","gee_binomial","glm_gaussian","glm_binomial","lme_gaussian","lme_binomial"] else ''
	
	##### import R packages #####
	if method in ["gee_gaussian","gee_binomial"]:
		try:
			geepack = importr('geepack')
		except RRuntimeError:
			print Error("unable to import R package 'geepack'")
			return
	if method in ["lme_gaussian","lme_binomial"]:
		try:
			lme4 = importr('lme4')
		except RRuntimeError:
			print Error("unable to import R package 'lme4'")
			return
	if method == "coxph":
		try:
			coxph = importr('survival')
		except RRuntimeError:
			print Error("unable to import R package 'survival''")
			return

	if focus: focus = focus.split(',')
	
	##### READ model VARIABLES FROM FILE #####
	print "   ... extracting model variables and removing missing/invalid samples"
	model_vars_dict = {}
	dependent = re.split('\\~',model)[0]
	independent = re.split('\\~',model)[1]
	vars_df = pd.read_table(pheno,sep='\t',dtype='str')
	for x in list(vars_df.columns) + ['marker','marker1','marker2','marker.interact']:
		mtype = ''
		if dependent.find(x) != -1:
			pre = dependent.split(x)[0] if dependent.split(x)[0] != '' else '.'
			post = dependent.split(x)[1] if dependent.split(x)[1] != '' else '.'
			if not pre[-1].isalpha() and not post[0].isalpha():
				mtype = 'dependent'
		if independent.find(x) != -1:
			pre = independent.split(x)[0] if independent.split(x)[0] != '' else '.'
			post = independent.split(x)[1] if independent.split(x)[1] != '' else '.'
			if not pre[-1].isalpha() and not post[0].isalpha():
				if mtype == '':
					mtype = 'independent'
				else:
					print Error("a column in the phenotype file is defined in the model as both an independent and dependent variable")
					return
		if mtype != '':
			if model[model.find(x)-7:model.find(x)] == 'factor(':
				model_vars_dict[x] = {'class': 'factor', 'type': mtype}
			elif model[model.find(x)-15:model.find(x)] == 'ordered(factor(':
				model_vars_dict[x] = {'class': 'orderedfactor', 'type': mtype}
			elif model[model.find(x)-3:model.find(x)] == '(1|':
				model_vars_dict[x] = {'class': 'random', 'type': mtype}
			elif model[model.find(x)-8:model.find(x)] == 'cluster(':
				model_vars_dict[x] = {'class': 'cluster', 'type': mtype}
			else:
				model_vars_dict[x] = {'class': 'numeric', 'type': mtype}
	print "   ... analysis model: %s" % model

	for x in model_vars_dict.keys():
		if x in list(vars_df.columns):
			print "          %s variable %s found" % (model_vars_dict[x]['type'], x)
		elif x in ['marker','marker1','marker2','marker.interact']:
			print "          %s variable %s skipped" % (model_vars_dict[x]['type'], x)
		else:
			print "          %s variable %s not found" % (model_vars_dict[x]['type'], x)
			print Error("model variable missing from phenotype file")
			return
	
	if sex:
		if sex in list(vars_df.columns):
			print "          sex column %s found" % sex
		else:
			print "          sex column %s not found" % sex
			print Error("sex column missing from phenotype file")
			return

	vars_df = vars_df[list(set([a for a in [fid,iid,sex] if a] + list([a for a in model_vars_dict.keys() if a != 'marker'])))]
	
	nmale = len(vars_df[sex][vars_df[sex] == male]) if sex and male and female else 'NA'
	nfemale = len(vars_df[sex][vars_df[sex] == female]) if sex and male and female else 'NA'
	
	vars_df[fid] = vars_df[fid].astype(str)
	vars_df[iid] = vars_df[iid].astype(str)
	
	##### EXTRACT CASE/CTRL IF BINOMIAL fxn #####
	for x in model_vars_dict.keys():
		if model_vars_dict[x]['type'] == 'dependent' and fxn == 'binomial':
			vars_df = vars_df[vars_df[x].isin([int(case),int(ctrl)])]
			vars_df[x] = vars_df[x].map({int(ctrl): 0, int(case): 1})
	vars_df.dropna(inplace = True)
	#for i in model_vars_dict.keys():
	#	if model_vars_dict[i]['class'] in ['factor','random']:
	#		vars_df[i] = pd.Categorical.from_array(vars_df[i]).codes.astype(np.int64)
	if len(vars_df.index) == 0:
		print Error("no data left for analysis")
		return
		
	##### DETERMINE MODEL STATS TO BE EXTRACTED #####
	if not focus:
		focus = ['(Intercept)'] if method.split('_')[0] in ['gee','glm','lme'] else []
		for x in re.sub("\+|\~|\-",",",model.split('~')[1]).split(','):
			if not x[0] == '(' and not x[-1] == ')':
				if x.find('factor(') != -1:
					focus.append(x + str(max(vars_df[re.sub('factor\(|\)','',x)])))
				elif x.find('*') != -1:
					focus.append('*'.join(sorted(x.split('*'))))
				else:
					focus.append(x)
	
	print "   ... reading sample list"
	sample_ids = []
	open_func = gzip.open if samples[-3:] == '.gz' else open
	with open_func(samples) as sf:
		lines = (line.rstrip() for line in sf)
		lines = (line for line in lines if line)
		for line in lines:
			sample_ids.append(line)
	if len(vars_df[vars_df[iid].isin(sample_ids)]) == 0:
		print Error("phenotype file and data file contain no common samples")
		return
	
	samples = len(vars_df.index)
	samples_unique = len(vars_df.drop_duplicates(subset=[iid]).index)
	clusters = len(vars_df.drop_duplicates(subset=[fid]).index.values)
	dep_var = [key for key in model_vars_dict if model_vars_dict[key]['type'] == 'dependent']
	cases = len(vars_df[dep_var[0]][vars_df[dep_var[0]].isin([1])]) if fxn == 'binomial' else 'NA'
	ctrls = len(vars_df[dep_var[0]][vars_df[dep_var[0]].isin([0])]) if fxn == 'binomial' else 'NA'
	print "   ... data summary"
	print "          " + str(samples) + " total observations"
	print "          " + str(samples_unique) + " unique samples"
	print "          " + str(clusters) + " clusters"
	print "          " + str(cases) + " case"
	print "          " + str(ctrls) + " control"
	print "          " + str(nmale) + " male"
	print "          " + str(nfemale) + " female"
	
	##### DETERMINE MARKERS TO BE ANALYZED #####
	if region_list:
		print "   ... reading list of regions from file"
		marker_list = Coordinates(region_list).Load()
	elif region:
		if len(region.split(':')) > 1:
			marker_list = pd.DataFrame({'chr': [re.split(':|-',region)[0]],'start': [re.split(':|-',region)[1]],'end': [re.split(':|-',region)[2]],'region': [region]})
		else:
			marker_list = pd.DataFrame({'chr': [region],'start': ['NA'],'end': ['NA'],'region': [region]})
	else:
		marker_list = pd.DataFrame({'chr': [str(i+1) for i in range(26)],'start': ['NA' for i in range(26)],'end': ['NA' for i in range(26)],'region': [str(i+1) for i in range(26)]})
	marker_list['n'] = 0
	tb = tabix.open(data)
	for i in range(len(marker_list.index)):
		try:
			records = tb.querys(marker_list['region'][i])
		except:
			pass
		else:
			for record in records:
				if marker_list['start'][i] != 'NA':
					marker_list['n'][i] = marker_list['n'][i] + 1
				else:
					marker_list['n'][i] = 1
					break
	marker_list = marker_list[marker_list['n'] > 0].reset_index(drop=True)
	
	if marker_list['n'].sum() == 0:
		print Error("no markers found")
		return()
	else:
		print "          " + str(len(marker_list.index)) + " non-empty regions"

	sig = int(sig) if sig else sig
	buffer = int(buffer) if buffer else buffer

	print "   ... starting marker analysis"
	written = False
	bgzfile = bgzf.BgzfWriter(out + '.gz', 'wb')
	tb = tabix.open(data)
	for r in range(len(marker_list.index)):
		reg = marker_list['region'][r]
		chr = reg.split(':')[0]
		try:
			records = tb.querys(reg)
		except:
			pass
		else:
			i = 0
			while True:
				i = i + 1
				chunk=list(islice(records, buffer))
				if not chunk:
					break
				chunkdf = pd.DataFrame(chunk)
				marker_info = chunkdf.ix[:,:4]
				marker_info.columns = ['chr','pos','marker','a1','a2'] if format == 'dos2' else ['chr','marker','pos','a1','a2']
				marker_info['marker_unique'] = 'chr' + marker_info['chr'].astype(str) + 'bp' + marker_info['pos'].astype(str) + '.'  + marker_info['marker'].astype(str) + '.'  + marker_info['a1'].astype(str) + '.'  + marker_info['a2'].astype(str)
				marker_info.index = marker_info['marker_unique']
				marker_data = chunkdf.ix[:,5:].transpose()
				marker_data = marker_data.convert_objects(convert_numeric=True)
				marker_data.columns = marker_info['marker_unique']
				if format == 'oxford':
					marker_data = marker_data.apply(lambda col: pd.Series(np.array(ConvertDosage(list(col))).astype(np.float64)),0)
				marker_data[iid] = sample_ids
				model_df = pd.merge(vars_df, marker_data, on = [iid], how='left').sort([fid])
				marker_info['callrate']=marker_data.drop_duplicates(subset=[iid])[marker_info['marker_unique']].apply(lambda col: CalcCallrate(col), 0)
				if sex and male and female:
					male_idx = model_df[model_df[sex].isin([male])].index.values
					female_idx = model_df[model_df[sex].isin([female])].index.values
				else:
					male_idx = None
					female_idx = None
				marker_info['freq']=model_df.drop_duplicates(subset=[iid])[marker_info['marker_unique']].apply(lambda col: CalcFreq(marker=col, chr = chr, male_idx = male_idx, female_idx = female_idx))
				unrelated_ids = model_df.drop_duplicates(subset=[fid]).index.values
				marker_info['freq.unrel']=model_df.drop_duplicates(subset=[iid]).loc[unrelated_ids][marker_info['marker_unique']].apply(lambda col: CalcFreq(marker=col, chr = chr, male_idx = male_idx, female_idx = female_idx))
				if fxn == 'binomial':
					marker_info['freq.ctrl']=model_df.drop_duplicates(subset=[iid])[model_df[dep_var[0]] == 0][marker_info['marker_unique']].apply(lambda col: CalcFreq(marker=col, chr = chr, male_idx = male_idx, female_idx = female_idx))
					marker_info['freq.case']=model_df.drop_duplicates(subset=[iid])[model_df[dep_var[0]] == 1][marker_info['marker_unique']].apply(lambda col: CalcFreq(marker=col, chr = chr, male_idx = male_idx, female_idx = female_idx))
					marker_info['freq.unrel.ctrl']=model_df.drop_duplicates(subset=[iid]).loc[unrelated_ids][model_df[dep_var[0]] == 0][marker_info['marker_unique']].apply(lambda col: CalcFreq(marker=col, chr = chr, male_idx = male_idx, female_idx = female_idx))
					marker_info['freq.unrel.case']=model_df.drop_duplicates(subset=[iid]).loc[unrelated_ids][model_df[dep_var[0]] == 1][marker_info['marker_unique']].apply(lambda col: CalcFreq(marker=col, chr = chr, male_idx = male_idx, female_idx = female_idx))
				marker_info['rsq']=model_df.drop_duplicates(subset=[iid])[marker_info['marker_unique']].apply(lambda col: CalcRsq(col), 0)
				marker_info['rsq.unrel']=model_df.drop_duplicates(subset=[iid]).loc[unrelated_ids][marker_info['marker_unique']].apply(lambda col: CalcRsq(col), 0)
				if fxn == 'binomial':
					marker_info['rsq.ctrl']=model_df.drop_duplicates(subset=[iid])[model_df[dep_var[0]] == 0][marker_info['marker_unique']].apply(lambda col: CalcRsq(col), 0)
					marker_info['rsq.case']=model_df.drop_duplicates(subset=[iid])[model_df[dep_var[0]] == 1][marker_info['marker_unique']].apply(lambda col: CalcRsq(col), 0)
					marker_info['rsq.unrel.ctrl']=model_df.drop_duplicates(subset=[iid]).loc[unrelated_ids][model_df[dep_var[0]] == 0][marker_info['marker_unique']].apply(lambda col: CalcRsq(col), 0)
					marker_info['rsq.unrel.case']=model_df.drop_duplicates(subset=[iid]).loc[unrelated_ids][model_df[dep_var[0]] == 1][marker_info['marker_unique']].apply(lambda col: CalcRsq(col), 0)
				marker_info['hwe']=model_df.drop_duplicates(subset=[iid])[marker_info['marker_unique']].apply(lambda col: CalcHWE(marker=col, chr=chr, female_idx=female_idx), 0)
				marker_info['hwe.unrel']=model_df.drop_duplicates(subset=[iid]).loc[unrelated_ids][marker_info['marker_unique']].apply(lambda col: CalcHWE(marker=col, chr=chr, female_idx=female_idx), 0)
				if fxn == 'binomial':
					marker_info['hwe.ctrl']=model_df.drop_duplicates(subset=[iid])[model_df[dep_var[0]] == 0][marker_info['marker_unique']].apply(lambda col: CalcHWE(marker=col, chr=chr, female_idx=female_idx), 0)
					marker_info['hwe.case']=model_df.drop_duplicates(subset=[iid])[model_df[dep_var[0]] == 1][marker_info['marker_unique']].apply(lambda col: CalcHWE(marker=col, chr=chr, female_idx=female_idx), 0)
					marker_info['hwe.unrel.ctrl']=model_df.drop_duplicates(subset=[iid]).loc[unrelated_ids][model_df[dep_var[0]] == 0][marker_info['marker_unique']].apply(lambda col: CalcHWE(marker=col, chr=chr, female_idx=female_idx), 0)
					marker_info['hwe.unrel.case']=model_df.drop_duplicates(subset=[iid]).loc[unrelated_ids][model_df[dep_var[0]] == 1][marker_info['marker_unique']].apply(lambda col: CalcHWE(marker=col, chr=chr, female_idx=female_idx), 0)
				marker_info['filter']=marker_info.apply(lambda row: GenerateFilterCode(marker_info=row, miss=miss, freq=freq, rsq=rsq, hwe=hwe), 1)
				marker_info['samples'] = str(samples) + '/' + str(samples_unique) + '/' + str(clusters) + '/' + str(cases) + '/' + str(ctrls)
				markercols = [col for col in model_df.columns if 'chr' in col]
				model_df[markercols] = model_df[markercols].astype(float)
				for x in model_vars_dict.keys():
					if model_vars_dict[x]['class'] == 'factor':
						model_df[x] = pd.Categorical.from_array(model_df[x]).codes.astype(np.int64)
				for x in [a for a in model_vars_dict.keys() if a != 'marker']:
					if model_vars_dict[x]['class'] not in ['factor','random','cluster']:
						model_df[x] = model_df[x].astype(float)
				if method.split('_')[0] in ['gee','glm','lme','coxph']:
					if method.split('_')[0] == 'gee':
						model_df[fid] = pd.Categorical.from_array(model_df[fid]).codes.astype(np.int64)
						model_df.sort([fid],inplace = True)
						results = marker_info.apply(lambda row: CalcGEE(marker_info=row, model_df=model_df, model_vars_dict=model_vars_dict, model=model, iid=iid, fid=fid, method=method, fxn=fxn, focus=focus, dep_var=dep_var), 1)
					elif method.split('_')[0] == 'glm':
						results = marker_info.apply(lambda row: CalcGLM(marker_info=row, model_df=model_df, model_vars_dict=model_vars_dict, model=model, iid=iid, fid=fid, method=method, fxn=fxn, focus=focus, dep_var=dep_var), 1)
					elif method.split('_')[0] == 'lme':
						results = marker_info.apply(lambda row: CalcLME(marker_info=row, model_df=model_df, model_vars_dict=model_vars_dict, model=model, iid=iid, fid=fid, method=method, fxn=fxn, focus=focus, dep_var=dep_var), 1)
					elif method == 'coxph':
						results = marker_info.apply(lambda row: CalcCoxPH(marker_info=row, model_df=model_df, model_vars_dict=model_vars_dict, model=model, iid=iid, fid=fid, method=method, fxn=fxn, focus=focus, dep_var=dep_var), 1)
					results.fillna('NA', inplace=True)
					if nofail:
						results = results[results['status'] > 0]
					if 'reg_id' in marker_list.columns:
						results['reg_id'] = marker_list['reg_id'][r]
					if 'marker_unique' in results.columns.values:
						results.drop('marker_unique',axis=1,inplace=True)
					if not written:
						bgzfile.write("\t".join(['#' + x if x == 'chr' else x for x in results.columns.values.tolist()]) + '\n')
						bgzfile.flush()
						written = True
					results.to_csv(bgzfile, header=False, sep='\t', index=False)
				else:
					if method == 'efftests':
						if i == 1:
							reg_model_df = model_df.drop(marker_info['marker_unique'][marker_info['filter'] != 0],axis=1)
							reg_marker_info = marker_info[marker_info['filter'] == 0]
						else:
							reg_model_df = pd.merge(reg_model_df,model_df.drop(marker_info['marker_unique'][marker_info['filter'] != 0],axis=1),on=[iid],how='left',copy=False)
							reg_marker_info = reg_marker_info.append(marker_info[marker_info['filter'] == 0],ignore_index=True)
				cur_markers = str(min(i*buffer,marker_list['n'][r])) if marker_list['start'][r] != 'NA' else str(i*buffer)
				tot_markers = str(marker_list['n'][r]) if marker_list['start'][r] != 'NA' else '> 0'
				print '   ... processed ' + cur_markers + ' of ' + tot_markers + ' markers from region ' + str(r+1) + ' of ' + str(len(marker_list.index))
			if method == 'efftests':
				tot_tests = reg_marker_info.shape[0]
				if tot_tests > 0:
					if (tot_tests * tot_tests) / 100000000.0 <= mem:
						n_eff = CalcEffTests(model_df=reg_model_df[reg_marker_info['marker_unique']], mem=mem)
						status = 0
					else:
						n_eff = float('nan')
						status = 2
				else:
					n_eff, tot_tests, status = (0, 0, 1)
				results = pd.DataFrame({'chr': [marker_list['chr'][r]], 'start': [marker_list['start'][r]], 'end': [marker_list['end'][r]], 'reg_id': [marker_list['reg_id'][r]], 'n_total': [tot_tests], 'n_eff': [n_eff], 'status': [status]})[['chr','start','end','reg_id','n_total','n_eff','status']]
				results.fillna('NA', inplace=True)
				if nofail:
					results = results[results['status'] > 0]
				if 'reg_id' in marker_list.columns:
					results['reg_id'] = marker_list['reg_id'][r]
				if 'marker_unique' in results.columns.values:
					results.drop('marker_unique',axis=1,inplace=True)
				if not written:
					bgzfile.write("\t".join(['#' + x if x == 'chr' else x for x in results.columns.values.tolist()]) + '\n')
					bgzfile.flush()
					written = True
				results.to_csv(bgzfile, header=False, sep='\t', index=False)
				print '   ... processed effective tests calculation for region ' + str(r+1) + ' of ' + str(len(marker_list.index))
	bgzfile.close()
	print "   ... mapping results file"
	cmd = 'tabix -b 2 -e 2 ' + out + '.gz'
	p = subprocess.Popen(cmd, shell=True)
	p.wait()	
	print "   ... process complete"