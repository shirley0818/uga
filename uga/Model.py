import os
import sys
import getopt
import subprocess
import gzip
import tabix
import math
import numpy as np
import pandas as pd
from rpy2.robjects.packages import importr
import pandas.rpy.common as py2r
import re
from itertools import islice,takewhile
from Bio import bgzf
import psutil
from MarkerCalc import Complement,ConvertDosage,CalcCallrate,CalcFreq,CalcRsq,CalcHWE,CallToDos
from Messages import Error
from Stats import GenerateFilterCode,CalcGEE,CalcGLM,CalcLME,CalcCoxPH,CalcEffTests,CalcFamSkatO,CalcFamSkat
from Coordinates import Coordinates
from Pheno import ExtractModelVars
from plinkio import plinkfile
import collections
import pysam
import vcf as VCF
from memory_profiler import profile, memory_usage

pd.options.mode.chained_assignment = None

@profile
def Model(out = None, 
			data = None, 
			format = 'oxford', 
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
			region_id = None, 
			pedigree = None, 
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
			mem = 3, 
			corstr = 'exchangeable', 
			delimiter = 'tab', 
			nofail = False):

	print "model options ..."
	for arg in locals().keys():
		if not str(locals()[arg]) in ['None','False']:
			print "   {0:>{1}}".format(str(arg), len(max(locals().keys(),key=len))) + ": " + str(locals()[arg])

	assert out, Error("an output file must be specified")
	assert data, Error("a genotype data file must be specified")
	assert samples or format == 'plink' or format == 'vcf', Error("a sample file must be specified if not Plink format")
	assert pheno, Error("a phenotype file must be specified")
	assert model, Error("a model must be specified")
	assert fid, Error("a family ID column must be specified")
	assert iid, Error("an individual ID column must be specified")
	assert method, Error("an analysis method must be specified")
	
	if delimiter == 'tab':
		delimiter = '\t'
	elif delimiter == 'space':
		delimiter = ' '
	else:
		delimiter = ','
	
	##### READ model VARIABLES FROM FILE #####
	print "extracting model variables and removing missing/invalid samples ..."
	fxn = method.split('_')[1] if method in ["gee_gaussian","gee_binomial","glm_gaussian","glm_binomial","lme_gaussian","lme_binomial"] else None
	vars_df, model_vars_dict = ExtractModelVars(pheno,model,fid,iid,fxn=fxn,sex=sex,delimiter=delimiter)

	##### DETERMINE MODEL STATS TO BE EXTRACTED #####
	if focus: 
		focus = focus.split(',')
	else:
		focus = ['(Intercept)'] if method.split('_')[0] in ['gee','glm','lme'] else []
		for x in re.sub("\+|\~|\-",",",model.split('~')[1]).split(','):
			if not x[0] == '(' and x.find('cluster(') == -1:
				if x.find('factor(') != -1:
					for v in vars_df[re.sub('factor\(|\)','',x)].unique().astype(np.int64) - min(vars_df[re.sub('factor\(|\)','',x)].unique().astype(np.int64)):
						if v != min(vars_df[re.sub('factor\(|\)','',x)].unique().astype(np.int64) - min(vars_df[re.sub('factor\(|\)','',x)].unique().astype(np.int64))):
							focus.append(x + str(v))
				elif x.find('*') != -1:
					focus.append('*'.join(sorted(x.split('*'))))
				else:
					focus.append(x)

	##### LOAD ITERATORS, ELSE LOAD SAMPLE LIST FILE #####
	if format == 'plink':
		print "reading Plink binary files"
		plink_bed_it = plinkfile.open(data)
		plink_sample_it = plink_bed_it.get_samples()
		plink_locus_it = plink_bed_it.get_loci()
		sample_ids = [x.iid for x in plink_sample_it]
	elif format == 'vcf':
		print "reading vcf file"
		tb = tabix.open(data)
		v=VCF.Reader(filename=data)
		record=v.next()
		sample_ids = [a.sample for a in record.samples]
	else:
		print "reading data and sample files"
		tb = tabix.open(data)
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
	
	##### REDUCE PHENO DATA TO GENOTYPE IDs #####
	vars_df = vars_df[vars_df[iid].isin(sample_ids)]

	##### CREATE SUMMARY FOR DATA TO BE ANALYZED #####
	samples = len(vars_df.index)
	vars_df_nodup = vars_df.drop_duplicates(subset=[iid])
	samples_unique = len(vars_df_nodup.index)
	clusters = len(vars_df_nodup.drop_duplicates(subset=[fid]).index)
	dep_var = [key for key in model_vars_dict if model_vars_dict[key]['type'] == 'dependent']
	cases = len(vars_df_nodup[dep_var[0]][vars_df_nodup[dep_var[0]].isin(['1'])]) if fxn == 'binomial' else 'NA'
	ctrls = len(vars_df_nodup[dep_var[0]][vars_df_nodup[dep_var[0]].isin(['0'])]) if fxn == 'binomial' else 'NA'
	nmale = len(vars_df_nodup[vars_df_nodup[sex].isin([str(male)])].index.values) if not sex is None and not male is None and not female is None else 'NA'
	nfemale = len(vars_df_nodup[vars_df_nodup[sex].isin([str(female)])].index.values) if not sex is None and not male is None and not female is None else 'NA'
	print "data summary ..."
	print "   " + str(samples) + " total observations"
	print "   " + str(samples_unique) + " unique samples"
	print "   " + str(clusters) + " clusters"
	print "   " + str(cases) + " case"
	print "   " + str(ctrls) + " control"
	print "   " + str(nmale) + " male"
	print "   " + str(nfemale) + " female"
	
	##### READ PEDIGREE FROM FILE FOR FAMILY BASED SKAT TEST #####
	if pedigree:
		print "extracting pedigree from file"
		pedigree = pd.read_table(pedigree,sep='\t',dtype='str',header=None, names=['FID','IID','PAT','MAT'])
		pedigree = pedigree[pedigree['IID'].isin(list(vars_df[iid].values))]

	##### GENERATE REGION LIST #####
	if region_list:
		print "reading list of regions from file"
		marker_list = Coordinates(region_list).Load()
	elif region:
		if len(region.split(':')) > 1:
			marker_list = pd.DataFrame({'chr': [re.split(':|-',region)[0]],'start': [re.split(':|-',region)[1]],'end': [re.split(':|-',region)[2]],'region': [region]})
		else:
			marker_list = pd.DataFrame({'chr': [region],'start': ['NA'],'end': ['NA'],'region': [region]})
		marker_list['reg_id'] = region_id
	else:
		marker_list = pd.DataFrame({'chr': [str(i+1) for i in range(26)],'start': ['NA' for i in range(26)],'end': ['NA' for i in range(26)],'region': [str(i+1) for i in range(26)]})
	marker_list['n'] = 0
	
	##### DETERMINE NONEMPTY REGIONS #####
	if format == 'plink':
		for i in range(len(marker_list.index)):
			if marker_list['start'][i] != 'NA':
				marker_list['n'][i] = len([c for c in plink_locus_it if c.chromosome == int(marker_list['chr'][i]) and c.bp_position >= int(marker_list['start'][i]) and c.bp_position <= int(marker_list['end'][i])])
			else:
				marker_list['n'][i] = len(plink_locus_it)
	else:
		tb = tabix.open(data)
		for i in range(len(marker_list.index)):
			try:
				records = tb.querys(marker_list['region'][i])
			except:
				pass
			else:
				for record in records:
					if marker_list['start'][i] != 'NA' and int(marker_list['end'][i]) - int(marker_list['start'][i]) <= 10000000:
						marker_list['n'][i] = marker_list['n'][i] + 1
					else:
						marker_list['n'][i] = 'n'
						break
	marker_list = marker_list[marker_list['n'] > 0].reset_index(drop=True)
	if marker_list['n'].sum() == 0:
		print Error("no markers found")
		return()
	else:
		print "   " + str(len(marker_list.index)) + " non-empty regions"

	##### SET BUFFER AND SIG DIGITS #####
	sig = int(sig) if sig else sig
	buffer = int(buffer) if buffer else buffer

	##### START ANALYSIS #####
	print "modelling data ..."
	written = False
	bgzfile = bgzf.BgzfWriter(out + '.gz', 'wb')
	for r in range(len(marker_list.index)):
		reg = marker_list['region'][r]
		chr = reg.split(':')[0]
		i = 0
		if format == 'plink':
			if reg == chr:
				try:
					records = (x for x in plink_locus_it if x.chromosome == int(chr))
				except:
					break
			else:
				try:
					records = (x for x in plink_locus_it if x.chromosome == int(chr) and x.bp_position >= int(marker_list['start'][r]) and x.bp_position <= int(marker_list['end'][r]))
				except:
					break
		else:
			try:
				records = tb.querys(reg)
			except:
				break
		while True:
			i = i + 1
			chunk=list(islice(records, buffer))
			if not chunk:
				break
			if format == 'plink':
				marker_info=collections.OrderedDict()
				marker_info['chr'] = collections.OrderedDict()
				marker_info['pos'] = collections.OrderedDict()
				marker_info['marker'] = collections.OrderedDict()
				marker_info['a1'] = collections.OrderedDict()
				marker_info['a2'] = collections.OrderedDict()
				marker_data=collections.OrderedDict()
				for locus, row in zip(chunk, plink_bed_it):
					if locus.allele1 == '0':
						locus.allele1 = locus.allele2
					marker_unique = 'chr' + str(locus.chromosome) + 'bp' + str(locus.bp_position) + '.'  + locus.name + '.' + locus.allele2 + '.' + locus.allele1
					marker_info['chr'][marker_unique] = locus.chromosome
					marker_info['marker'][marker_unique] = locus.name
					marker_info['pos'][marker_unique] = locus.bp_position
					marker_info['a1'][marker_unique] = locus.allele2
					marker_info['a2'][marker_unique] = locus.allele1
					for sample, geno in zip(plink_sample_it, row):
						if not marker_unique in marker_data.keys():
							marker_data[marker_unique] = collections.OrderedDict({sample.iid: geno})
						else:
							marker_data[marker_unique][sample.iid] = geno if geno != 3 else 'NA'

				marker_info = pd.DataFrame(marker_info)
				marker_info['marker_unique'] = marker_info.index
				marker_data = pd.DataFrame(marker_data)
				marker_data = marker_data.convert_objects(convert_numeric=True)
				marker_data[iid] = marker_data.index
			else:
				chunkdf = pd.DataFrame(chunk)
				marker_info = chunkdf.ix[:,:4]
				marker_info.replace('.','NA',inplace=True)
				marker_info.columns = ['chr','pos','marker','a1','a2'] if format in ['dos2','vcf'] else ['chr','marker','pos','a1','a2']
				marker_info = marker_info[['chr','pos','marker','a1','a2']]
				marker_info['marker_unique'] = 'chr' + marker_info['chr'].astype(str) + 'bp' + marker_info['pos'].astype(str) + '.'  + marker_info['marker'].astype(str) + '.'  + marker_info['a1'].astype(str) + '.'  + marker_info['a2'].astype(str)
				marker_info.index = marker_info['marker_unique']
				if format == 'vcf':
					marker_data = chunkdf.ix[:,9:].transpose()
					marker_data=marker_data.applymap(CallToDos)
				elif format == 'oxford':
					marker_data = chunkdf.ix[:,5:].transpose()
					marker_data = marker_data.apply(lambda col: pd.Series(np.array(ConvertDosage(list(col))).astype(np.float64)),0)
				else:
					marker_data = chunkdf.ix[:,5:].transpose()
				marker_data = marker_data.convert_objects(convert_numeric=True)
				marker_data.columns = marker_info['marker_unique']
				marker_data[iid] = sample_ids
			model_df = pd.merge(vars_df, marker_data, on = [iid], how='left').sort([fid])
			model_df_nodup=model_df.drop_duplicates(subset=[iid]).reset_index(drop=True)
			marker_info['callrate']=model_df_nodup[marker_info['marker_unique']].apply(lambda col: CalcCallrate(col), 0)
			model_df_nodup_unrel=model_df_nodup.drop_duplicates(subset=[fid]).reset_index(drop=True)
			if sex and male and female:
				male_idx = model_df_nodup[model_df_nodup[sex].isin([male])].index.values
				female_idx = model_df_nodup[model_df_nodup[sex].isin([female])].index.values
			else:
				male_idx = None
				female_idx = None
			marker_info['freq']=model_df_nodup[marker_info['marker_unique']].apply(lambda col: CalcFreq(marker=col, chr = chr, male_idx = male_idx, female_idx = female_idx))
			marker_info['freq.unrel']=model_df_nodup_unrel[marker_info['marker_unique']].apply(lambda col: CalcFreq(marker=col, chr = chr, male_idx = male_idx, female_idx = female_idx))
			if fxn == 'binomial':
				marker_info['freq.ctrl']=model_df_nodup[model_df_nodup[dep_var[0]] == '0'][list(marker_info['marker_unique'])].apply(lambda col: CalcFreq(marker=col, chr = chr, male_idx = male_idx, female_idx = female_idx))
				marker_info['freq.case']=model_df_nodup[model_df_nodup[dep_var[0]] == '1'][list(marker_info['marker_unique'])].apply(lambda col: CalcFreq(marker=col, chr = chr, male_idx = male_idx, female_idx = female_idx))
				marker_info['freq.unrel.ctrl']=model_df_nodup_unrel[model_df_nodup_unrel[dep_var[0]] == '0'][list(marker_info['marker_unique'])].apply(lambda col: CalcFreq(marker=col, chr = chr, male_idx = male_idx, female_idx = female_idx))
				marker_info['freq.unrel.case']=model_df_nodup_unrel[model_df_nodup_unrel[dep_var[0]] == '1'][list(marker_info['marker_unique'])].apply(lambda col: CalcFreq(marker=col, chr = chr, male_idx = male_idx, female_idx = female_idx))
			marker_info['rsq']=model_df_nodup[marker_info['marker_unique']].apply(lambda col: CalcRsq(col), 0)
			marker_info['rsq.unrel']=model_df_nodup_unrel[marker_info['marker_unique']].apply(lambda col: CalcRsq(col), 0)
			if fxn == 'binomial':
				marker_info['rsq.ctrl']=model_df_nodup[model_df_nodup[dep_var[0]] == '0'][list(marker_info['marker_unique'])].apply(lambda col: CalcRsq(col), 0)
				marker_info['rsq.case']=model_df_nodup[model_df_nodup[dep_var[0]] == '1'][list(marker_info['marker_unique'])].apply(lambda col: CalcRsq(col), 0)
				marker_info['rsq.unrel.ctrl']=model_df_nodup_unrel[model_df_nodup_unrel[dep_var[0]] == '0'][list(marker_info['marker_unique'])].apply(lambda col: CalcRsq(col), 0)
				marker_info['rsq.unrel.case']=model_df_nodup_unrel[model_df_nodup_unrel[dep_var[0]] == '1'][list(marker_info['marker_unique'])].apply(lambda col: CalcRsq(col), 0)
			marker_info['hwe']=model_df_nodup[marker_info['marker_unique']].apply(lambda col: CalcHWE(marker=col, chr=chr, female_idx=female_idx), 0)
			marker_info['hwe.unrel']=model_df_nodup_unrel[marker_info['marker_unique']].apply(lambda col: CalcHWE(marker=col, chr=chr, female_idx=female_idx), 0)
			if fxn == 'binomial':
				marker_info['hwe.ctrl']=model_df_nodup[model_df_nodup[dep_var[0]] == '0'][list(marker_info['marker_unique'])].apply(lambda col: CalcHWE(marker=col, chr=chr, female_idx=female_idx), 0)
				marker_info['hwe.case']=model_df_nodup[model_df_nodup[dep_var[0]] == '1'][list(marker_info['marker_unique'])].apply(lambda col: CalcHWE(marker=col, chr=chr, female_idx=female_idx), 0)
				marker_info['hwe.unrel.ctrl']=model_df_nodup_unrel[model_df_nodup_unrel[dep_var[0]] == '0'][list(marker_info['marker_unique'])].apply(lambda col: CalcHWE(marker=col, chr=chr, female_idx=female_idx), 0)
				marker_info['hwe.unrel.case']=model_df_nodup_unrel[model_df_nodup_unrel[dep_var[0]] == '1'][list(marker_info['marker_unique'])].apply(lambda col: CalcHWE(marker=col, chr=chr, female_idx=female_idx), 0)
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
					results = marker_info.apply(lambda row: CalcGEE(marker_info=row, model_df=model_df, model_vars_dict=model_vars_dict, model=model, iid=iid, fid=fid, method=method, fxn=fxn, focus=focus, dep_var=dep_var, corstr=corstr), 1)
				elif method.split('_')[0] == 'glm':
					results = marker_info.apply(lambda row: CalcGLM(marker_info=row, model_df=model_df, model_vars_dict=model_vars_dict, model=model, iid=iid, fid=fid, method=method, fxn=fxn, focus=focus, dep_var=dep_var), 1)
				elif method.split('_')[0] == 'lme':
					results = marker_info.apply(lambda row: CalcLME(marker_info=row, model_df=model_df, model_vars_dict=model_vars_dict, model=model, iid=iid, fid=fid, method=method, fxn=fxn, focus=focus, dep_var=dep_var), 1)
				elif method == 'coxph':
					results = marker_info.apply(lambda row: CalcCoxPH(marker_info=row, model_df=model_df, model_vars_dict=model_vars_dict, model=model, iid=iid, fid=fid, method=method, fxn=fxn, focus=focus, dep_var=dep_var), 1)
				results.fillna('NA', inplace=True)
				if nofail:
					results = results[results['status'] > 0]
				if 'reg_id' in marker_list.columns and not marker_list['reg_id'][r] is None:
					results['reg_id'] = marker_list['reg_id'][r]
				if 'marker_unique' in results.columns.values:
					results.drop('marker_unique',axis=1,inplace=True)
				if not written:
					bgzfile.write("\t".join(['#' + x if x == 'chr' else x for x in results.columns.values.tolist()]) + '\n')
					bgzfile.flush()
					written = True
				results.to_csv(bgzfile, header=False, sep='\t', index=False)
			else:
				if method in ['efftests','famskat_o']:
					if i == 1:
						reg_model_df = model_df.drop(marker_info['marker_unique'][marker_info['filter'] != 0],axis=1)
						reg_marker_info = marker_info[marker_info['filter'] == 0]
					else:
						reg_model_df = pd.merge(reg_model_df,model_df.drop(marker_info['marker_unique'][marker_info['filter'] != 0],axis=1),how='outer',copy=False)
						reg_marker_info = reg_marker_info.append(marker_info[marker_info['filter'] == 0],ignore_index=True)
			cur_markers = str(min(i*buffer,marker_list['n'][r])) if marker_list['start'][r] != 'NA' else str(i*buffer)
			tot_markers = str(marker_list['n'][r]) if marker_list['start'][r] != 'NA' else '> 0'
			print '   processed ' + cur_markers + ' of ' + tot_markers + ' markers from region ' + str(r+1) + ' of ' + str(len(marker_list.index))
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
			print '   processed effective tests calculation for region ' + str(r+1) + ' of ' + str(len(marker_list.index))
		elif method == 'famskat_o':
			nmarkers = reg_marker_info.shape[0]
			if nmarkers > 0:
				reg_model_df.dropna(inplace=True)
				snp_info = pd.DataFrame({'Name': reg_marker_info['marker_unique'], 'gene': marker_list['reg_id'][r]})
				z = reg_model_df[list(marker_info['marker_unique'])]
				pheno = reg_model_df[list(set(model_vars_dict.keys() + [iid,fid]))]
				results_pre = CalcFamSkatO(snp_info=snp_info, z=z, model=model, pheno=pheno, pedigree=pedigree)
				results = pd.DataFrame({'chr': [marker_list['chr'][r]],'start': [marker_list['start'][r]],'end': [marker_list['end'][r]],'reg_id': [marker_list['reg_id'][r]],
										'p': [results_pre['p'][1]],'pmin': [results_pre['pmin'][1]],'rho': [results_pre['rho'][1]],'cmaf': [results_pre['cmaf'][1]],'nmiss': [results_pre['nmiss'][1]],
										'nsnps': [results_pre['nsnps'][1]],'errflag': [results_pre['errflag'][1]]})
				results = results[['chr','start','end','reg_id','p','pmin','rho','cmaf','nmiss','nsnps','errflag']]
				if not written:
					bgzfile.write("\t".join(['#' + x if x == 'chr' else x for x in results.columns.values.tolist()]) + '\n')
					bgzfile.flush()
					written = True
				results.to_csv(bgzfile, header=False, sep='\t', index=False)
	bgzfile.close()
	print "mapping results file"
	cmd = 'tabix -b 2 -e 2 ' + out + '.gz'
	p = subprocess.Popen(cmd, shell=True)
	p.wait()	
	print "process complete"
