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

from __main__ import *
import argparse
from __init__ import version
import textwrap
from datetime import date

class AddString(argparse.Action):
	def __call__(self, parser, namespace, values, option_string=None):
		if not 'ordered_args' in namespace:
			setattr(namespace, 'ordered_args', [])
		previous = namespace.ordered_args
		previous.append((self.dest, values))
		setattr(namespace, 'ordered_args', previous)

class AddTrue(argparse.Action):
	def __call__(self, parser, namespace, values, option_string=None):
		if not 'ordered_args' in namespace:
			setattr(namespace, 'ordered_args', [])
		previous = namespace.ordered_args
		previous.append((self.dest, True))
		setattr(namespace, 'ordered_args', previous)

class AddFalse(argparse.Action):
	def __call__(self, parser, namespace, values, option_string=None):
		if not 'ordered_args' in namespace:
			setattr(namespace, 'ordered_args', [])
		previous = namespace.ordered_args
		previous.append((self.dest, False))
		setattr(namespace, 'ordered_args', previous)

def Describe():
	print ''
	print 'uga v' + version + ' (c) 2015 Ryan Koesterer   GNU General Public License v3'
	print ''
	print textwrap.fill("Universal Genome Analyst is an open, flexible, and efficient tool for the distribution, management, and visualization of whole genome data analyses. It is designed to assist biomedical researchers in complex genomic data analysis through the use of a low level interface between the powerful R statistical environment and Python to allow for rapid integration of emerging analytical strategies. Researchers with access to a high performance computing cluster will find time-saving features for parallel analysis using a flexible, yet controlled, commandline interface.", initial_indent = '      ', subsequent_indent = '   ')
	print ''
	print textwrap.fill("This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.", initial_indent='   ', subsequent_indent='   ')
	print ''
	print textwrap.fill("This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.", initial_indent='   ', subsequent_indent='   ')
	print ''
	print textwrap.fill("You should have received a copy of the GNU General Public License along with this program.  If not, see <http://www.gnu.org/licenses/>", initial_indent='   ', subsequent_indent='   ')
	print ''

def Parser():
	parser = argparse.ArgumentParser(add_help=False, description=Describe())
	top_parser = argparse.ArgumentParser(parents=[parser])
	subparsers = top_parser.add_subparsers(title='modules', dest='which')

	top_parser.add_argument('--version', 
						action='version', 
						version='', 
						help='display version information and exit')

	##### SETTINGS PARSER #####
	settings_parser = subparsers.add_parser('set', help='user definable settings', parents=[parser])
	settings_parser.add_argument('--snpeff', 
						action=AddString, 
						help='set full path to snpEff executable')
	settings_parser.add_argument('--snpsift', 
						action=AddString, 
						help='set full path to SnpSift executable')
	settings_parser.add_argument('--dbnsfp', 
						action=AddString, 
						help='set full path to dbNSFP database')
	settings_parser.add_argument('--locuszoom', 
						action=AddString, 
						help='set full path to locuszoom executable')

	##### MODEL PARSER #####
	model_parser = subparsers.add_parser('model', help='variant and gene/region-based statistical modeling', parents=[parser])
	model_parser.add_argument('--out', 
						action=AddString, 
						help='output file basename (do not include path or extension)')
	model_parser.add_argument('--pheno', 
						action=AddString, 
						help='phenotype file')
	model_parser.add_argument('--varlist', 
						action=AddString, 
						help='variant list file')
	model_parser.add_argument('--fid', 
						action=AddString, 
						help='column name with family ID')
	model_parser.add_argument('--iid', 
						action=AddString, 
						help='column name with sample ID (The IDs in this column must match the --samples file)')
	model_parser.add_argument('--sep', 
						action=AddString, 
						choices=['tab','space','comma'], 
						help='phenotype file delimiter (default: tab)')
	model_parser.add_argument('--sample', 
						action=AddString, 
						help='sample file (not required for Plink format files)')
	model_parser.add_argument('--focus', 
						action=AddString, 
						help='comma separated list of variables for which stats will be reported (default: report all stats)')
	model_parser.add_argument('--sex', 
						action=AddString, 
						help='name of the column containing male/female status (requires --male and --female)')
	model_parser.add_argument('--male', 
						action=AddString, 
						type=int, 
						help='code for male (default: 1; requires --sex and --female)')
	model_parser.add_argument('--female', 
						action=AddString, 
						type=int, 
						help='code for female (default: 2; requires --sex and --male)')
	model_parser.add_argument('--buffer', 
						action=AddString, 
						type=int, 
						help='value for number of markers calculated at a time (WARNING: this argument will affect RAM memory usage; default: 100)')
	model_parser.add_argument('--miss', 
						action=AddString, 
						type=float, 
						help='threshold value for missingness (ie. 0.95 allows for up to 5%% missingness)')
	model_parser.add_argument('--maf', 
						action=AddString, 
						type=float, 
						help='threshold value for minimum minor allele frequency (ie. 0.03 filters out markers with maf < 0.03)')
	model_parser.add_argument('--maxmaf', 
						action=AddString, 
						type=float, 
						help='threshold value for maximum minor allele frequency (ie. 0.01 filters out markers with maf >= 0.01)')
	model_parser.add_argument('--rsq', 
						action=AddString, 
						type=float, 
						help='threshold value for imputation quality (ie. 0.8 filters out markers with rsq < 0.8)')
	model_parser.add_argument('--hwe', 
						action=AddString, 
						type=float, 
						help='threshold value for Hardy Weinberg p-value (ie. 1e-6 filters out markers with Hardy Weinberg p-value < 1e-6)')
	model_parser.add_argument('--case', 
						action=AddString, 
						type=int, 
						help='code for case in the dependent variable column (requires --ctrl; binomial fxn family only; default: 1)')
	model_parser.add_argument('--ctrl', 
						action=AddString, 
						type=int, 
						help='code for control in the dependent variable column (requires --case; binomial fxn family only; default: 0)')
	model_parser.add_argument('--corstr', 
						action=AddString, 
						choices=['exchangeable','independence','ar1','unstructured'], 
						help='correlation structure for gee analyses (default: exchangeable)')
	model_parser.add_argument('--ped', 
						action=AddString, 
						help='pedigree file')
	model_parser.add_argument('--replace', 
						nargs=0, 
						action=AddTrue, 
						help='replace any existing output files')
	model_parser.add_argument('--qsub', 
						action=AddString, 
						help='string indicating all qsub options to be added to the qsub command (trigger adds jobs to cluster queue')
	model_parser.add_argument('--id', 
						action=AddString, 
						help='add region id to results (for use with --region option)')
	model_parser.add_argument('--tag', 
						action=AddString, 
						help='add tag to column names (mainly for distinguishing multiple analyses)')
	model_parser.add_argument('--lmer-ctrl', 
						action=AddString, 
						default='check.nobs.vs.rankZ="stop",check.nlev.gtreq.5="stop",check.rankX="stop.deficient",check.scaleX="stop",check.conv.grad=.makeCC("stop",tol=1e-3,relTol=NULL),check.conv.singular=.makeCC(action="stop",tol=1e-4),check.conv.hess=.makeCC(action="stop",tol=1e-6)', 
						help='lmerControl parameters for gaussian lme models; use double quotes for string values (default: check.nobs.vs.rankZ="stop",check.nlev.gtreq.5="stop",check.rankX="stop.deficient",check.scaleX="stop",check.conv.grad=.makeCC("stop",tol=1e-3,relTol=NULL),check.conv.singular=.makeCC(action="stop",tol=1e-4),check.conv.hess=.makeCC(action="stop",tol=1e-6))')
	model_parser.add_argument('--reml', 
						nargs=0, 
						action=AddTrue, 
						help='REML value for lmer function')
	model_parser.add_argument('--cph-ctrl', 
						action=AddString, 
						default='eps=1e-09,toler.chol=.Machine$double.eps^0.75,iter.max=20,toler.inf=sqrt(1e-09),outer.max=10', 
						help='coxph.control parameters for coxph models; use double quotes for string values (default: eps=1e-09,toler.chol=.Machine$double.eps^0.75,iter.max=20,toler.inf=sqrt(1e-09),outer.max=10)')
	model_parser.add_argument('--meta', 
						action=AddString, 
						help='a meta analysis string')
	model_parser.add_argument('--lrt', 
						nargs=0, 
						action=AddTrue, 
						help='calculate likelihood ratio test p values using chi-square statistic')
	model_parser.add_argument('--rho', 
						action=AddString, 
						help='rho value in (0,1] for seqMeta skat-o models (default: 1; ex. 0.25 sets rho=c(0,0.25,0.5,0.75,1))')
	model_parser_split_group1 = model_parser.add_mutually_exclusive_group()
	model_parser_split_group1.add_argument('--region', 
						action=AddString, 
						help='genomic region specified in Tabix format (ie. 1:10583-1010582).')
	model_parser_split_group1.add_argument('--reglist', 
						action=AddString, 
						help='filename for a list of tabix format regions')
	model_parser_split_group2 = model_parser.add_mutually_exclusive_group()
	model_parser_split_group2.add_argument('--split', 
						nargs=0, 
						action=AddTrue, 
						help='split reglist into an individual job for each line in file (requires --reglist)')
	model_parser_split_group2.add_argument('--split-n', 
						action=AddString, 
						type=int, 
						help='split reglist into n individual jobs each with a subset of regions in the file (requires --reglist)')
	model_parser_split_group2.add_argument('--split-chr', 
						nargs=0, 
						action=AddTrue,  
						help='split data into chromosomes (will generate up to 26 separate jobs depending on chromosome coverage)')
	model_parser_split_group3 = model_parser.add_mutually_exclusive_group()
	model_parser_split_group3.add_argument('--job', 
						action=AddString, 
						type=int, 
						help='run a particular job (use with --reglist and --split with value a tabix format region or --split-n with value a number from 1..n)')
	model_parser_split_group3.add_argument('--jobs', 
						action=AddString, 
						help='filename for a list of jobs to run (use with --reglist and --split with a column of tabix format regions or --split-n with a column of numbers from 1..n)')
	model_parser.add_argument('--oxford', 
						action=AddString, 
						help='oxford format genotype data file')
	model_parser.add_argument('--dos1', 
						action=AddString, 
						help='dos1 format genotype data file')
	model_parser.add_argument('--dos2', 
						action=AddString, 
						help='dos2 format genotype data file')
	model_parser.add_argument('--plink', 
						action=AddString, 
						help='Plink binary format genotype data file (without extension)')
	model_parser.add_argument('--vcf', 
						action=AddString, 
						help='vcf 4.1/4.2 format genotype data file')
	model_parser.add_argument('--ggee', 
						action=AddString, 
						help='model string for gee gaussian analysis')
	model_parser.add_argument('--bgee', 
						action=AddString, 
						help='model string for gee binomial analysis')
	model_parser.add_argument('--gglm', 
						action=AddString, 
						help='model string for glm gaussian analysis')
	model_parser.add_argument('--bglm', 
						action=AddString, 
						help='model string for glm binomial analysis')
	model_parser.add_argument('--glme', 
						action=AddString, 
						help='model string for lme gaussian analysis')
	model_parser.add_argument('--blme', 
						action=AddString, 
						help='model string for lme binomial analysis')
	model_parser.add_argument('--cph', 
						action=AddString, 
						help='model string for coxph analysis')
	model_parser.add_argument('--neff', 
						action=AddString, 
						help='model string for li and ji effective test calculation (ensures that correct samples are included for relevant model)')
	model_parser.add_argument('--fskato', 
						action=AddString, 
						help='model string for family based skat-o analysis')
	model_parser.add_argument('--skat-method', 
						action=AddString,
						default='saddlepoint', 
						choices=['saddlepoint','integration','liu'], 
						help='seqMeta skatOMeta method (default: saddlepoint)')
	model_parser.add_argument('--skat-wts', 
						action=AddString,
						default='function(maf){dbeta(maf,1,25)}', 
						help='seqMeta skat weights (default: beta weights function(maf){dbeta(maf,1,25)})')
	model_parser.add_argument('--burden-wts', 
						action=AddString,
						default='function(maf){as.numeric(maf<0.01)}', 
						help='seqMeta burden weights (default: T1 weights function(maf){as.numeric(maf<0.01)})')
	model_parser.add_argument('--gskato', 
						action=AddString, 
						help='model string for skat-o gaussian analysis')
	model_parser.add_argument('--bskato', 
						action=AddString, 
						help='model string for skat-o binomial analysis')
	model_parser.add_argument('--fskat', 
						action=AddString, 
						help='model string for family based skat analysis')
	model_parser.add_argument('--gskat', 
						action=AddString, 
						help='model string for skat gaussian analysis')
	model_parser.add_argument('--bskat', 
						action=AddString, 
						help='model string for skat binomial analysis')
	model_parser.add_argument('--fburden', 
						action=AddString, 
						help='model string for family based burden analysis')
	model_parser.add_argument('--gburden', 
						action=AddString, 
						help='model string for burden  gaussian analysis')
	model_parser.add_argument('--bburden', 
						action=AddString, 
						help='model string for burden binomial analysis')

	##### META PARSER #####
	meta_parser = subparsers.add_parser('meta', help='meta-analysis', parents=[parser])
	meta_required = meta_parser.add_argument_group('required arguments')
	meta_parser.add_argument('--out', 
						action=AddString, 
						help='output file basename (do not include path or extension)')
	meta_parser.add_argument('--marker-col', 
						action=AddString, 
						help='variant(marker) name column')
	meta_parser.add_argument('--freq-col', 
						action=AddString, 
						help='effect allele frequency column')
	meta_parser.add_argument('--rsq-col', 
						action=AddString, 
						help='imputation quality column')
	meta_parser.add_argument('--hwe-col', 
						action=AddString, 
						help='hardy-weinberg p-value column')
	meta_parser.add_argument('--effect-col', 
						action=AddString, 
						help='effect column')
	meta_parser.add_argument('--stderr-col', 
						action=AddString, 
						help='standard error column')
	meta_parser.add_argument('--or-col', 
						action=AddString, 
						help='odds ratio column')
	meta_parser.add_argument('--z-col', 
						action=AddString, 
						help='z statistic column')
	meta_parser.add_argument('--p-col', 
						action=AddString, 
						help='p-value column')
	meta_parser.add_argument('--n-col', 
						action=AddString, 
						help='sample size column')
	meta_parser.add_argument('--gc', 
						action=AddString, 
						type=float, 
						help='set genomic inflation value instead of calculating it')
	meta_parser.add_argument('--n', 
						action=AddString, 
						help='set sample size')
	meta_parser.add_argument('--tag', 
						action=AddString, 
						help='tag for data file')
	meta_parser.add_argument('--file', 
						action=AddString, 
						help='results file name')
	meta_parser.add_argument('--meta', 
						action=AddString, 
						help='a meta analysis string')
	meta_parser.add_argument('--maf', 
						action=AddString, 
						type=float, 
						help='threshold value for minimum minor allele frequency (ie. 0.03 filters out markers with maf < 0.03)')
	meta_parser.add_argument('--rsq', 
						action=AddString, 
						type=float, 
						help='threshold value for imputation quality (ie. 0.8 filters out markers with rsq < 0.8)')
	meta_parser.add_argument('--hwe', 
						action=AddString, 
						type=float, 
						help='threshold value for Hardy Weinberg p-value (ie. 1e-6 filters out markers with Hardy Weinberg p-value < 1e-6)')
	meta_parser.add_argument('--method', 
						action=AddString, 
						choices=['sample_size', 'stderr'], 
						help='meta-analysis method (default: sample_size)')
	meta_parser.add_argument('--replace', 
						nargs=0, 
						action=AddTrue, 
						help='replace existing output files')
	meta_parser.add_argument('--qsub', 
						action=AddString, 
						help='string indicating all qsub options to be added to the qsub command')
	meta_parser.add_argument('--buffer', 
						action=AddString, 
						type=int, 
						help='value for number of markers calculated at a time (WARNING: this argument will affect RAM memory usage; default: 100)')
	meta_parser.add_argument('--id', 
						action=AddString, 
						help='add region id to results (for use with --region option)')
	meta_parser_split_group1 = meta_parser.add_mutually_exclusive_group()
	meta_parser_split_group1.add_argument('--region', 
						action=AddString, 
						help='genomic region specified in Tabix format (ie. 1:10583-1010582).')
	meta_parser_split_group1.add_argument('--reglist', 
						action=AddString, 
						help='filename for a list of tabix format regions')
	meta_parser_split_group2 = meta_parser.add_mutually_exclusive_group()
	meta_parser_split_group2.add_argument('--split', 
						nargs=0, 
						action=AddTrue, 
						help='split reglist into an individual job for each line in file (requires --reglist)')
	meta_parser_split_group2.add_argument('--split-n', 
						action=AddString, 
						type=int, 
						help='split reglist into n individual jobs each with a subset of regions in the file (requires --reglist)')
	meta_parser_split_group2.add_argument('--split-chr', 
						nargs=0, 
						action=AddTrue,  
						help='split data into chromosomes (will generate up to 26 separate jobs depending on chromosome coverage)')
	meta_parser_split_group3 = meta_parser.add_mutually_exclusive_group()
	meta_parser_split_group3.add_argument('--job', 
						action=AddString, 
						type=int, 
						help='run a particular job (use with --reglist and --split with value a tabix format region or --split-n with value a number from 1..n)')
	meta_parser_split_group3.add_argument('--jobs', 
						action=AddString, 
						help='filename for a list of jobs to run (use with --reglist and --split with a column of tabix format regions or --split-n with a column of numbers from 1..n)')

	##### MAP PARSER ######
	map_parser = subparsers.add_parser('map', help='map non-empty regions in genotype/imputed data files', parents=[parser])
	map_required = map_parser.add_argument_group('required arguments')
	map_required.add_argument('--out', 
						action=AddString, 
						required=True, 
						help='output file name')
	map_parser.add_argument('--replace', 
						nargs=0, 
						action=AddTrue, 
						help='replace any existing out files')
	map_parser.add_argument('--qsub', 
						action=AddString, 
						help='string indicating all qsub options to be added to the qsub command (trigger adds jobs to cluster queue')
	map_split_group1 = map_parser.add_mutually_exclusive_group()
	map_split_group1.add_argument('--mb', 
						action=AddString, 
						help='region size (megabase)')
	map_split_group1.add_argument('--kb', 
						action=AddString, 
						help='region size (kilobase)')
	map_split_group1.add_argument('--b', 
						action=AddString, 
						help='region size (base)')
	map_split_group1.add_argument('--n', 
						action=AddString, 
						help='number of markers to be included in each region')
	map_split_group2 = map_parser.add_mutually_exclusive_group()
	map_split_group2.add_argument('--oxford', 
						action=AddString, 
						help='oxford format genotype data file')
	map_split_group2.add_argument('--dos1', 
						action=AddString, 
						help='dos1 format genotype data file')
	map_split_group2.add_argument('--dos2', 
						action=AddString, 
						help='dos2 format genotype data file')
	map_split_group2.add_argument('--plink', 
						action=AddString, 
						help='Plink binary format genotype data file (without extension)')					
	map_split_group2.add_argument('--vcf', 
						action=AddString, 
						help='vcf 4.1/4.2 format genotype data file')
	map_split_group3 = map_parser.add_mutually_exclusive_group()
	map_split_group3.add_argument('--shift-mb', 
						action=AddString, 
						help='shift size (megabase)')
	map_split_group3.add_argument('--shift-kb', 
						action=AddString, 
						help='shift size (kilobase)')
	map_split_group3.add_argument('--shift-b', 
						action=AddString, 
						help='shift size (base)')
	map_split_group4 = map_parser.add_mutually_exclusive_group()
	map_split_group4.add_argument('--chr', 
						action=AddString, 
						type=int,  
						help='chromosome number from 1-26')
	map_split_group4.add_argument('--region', 
						action=AddString, 
						help='genomic region specified in Tabix format (ie. 1:10583-1010582).')

	##### COMPILE PARSER #####
	compile_parser = subparsers.add_parser('compile', help='verify and compile results files', parents=[parser])
	compile_required = compile_parser.add_argument_group('required arguments')
	compile_required.add_argument('--out', 
						action=AddString, 
						required=True, 
						help='filename for compiled results')
	compile_required.add_argument('--data', 
						action=AddString, 
						required=True, 
						help='base filename of existing results (basename only: do not include path or extension or list / region portion of filename; ex. set to X if out file names are of the form chr2/X.chr2bp1-2.gz or list0-99/X.list1.gz)')
	compile_parser.add_argument('--replace', 
						nargs=0, 
						action=AddTrue, 
						help='replace any existing output files')

	##### EXPLORE PARSER #####
	explore_parser = subparsers.add_parser('explore', help='explore results: filter, plot, list top results, etc.', parents=[parser])
	explore_required = explore_parser.add_argument_group('required arguments')
	explore_required.add_argument('--data', 
						action=AddString, 
						required=True, 
						help='filename for compiled results')
	explore_required.add_argument('--out', 
						action=AddString, 
						required=True, 
						help='output filename (basename only: do not include path)')
	explore_parser.add_argument('--qsub', 
						action=AddString, 
						help='string indicating all qsub options to be added to the qsub command (trigger adds jobs to cluster queue')
	explore_parser.add_argument('--qq', 
						nargs=0, 
						action=AddTrue, 
						help='print qq plot')
	explore_parser.add_argument('--qq-strat', 
						nargs=0, 
						action=AddTrue, 
						help='print frequency stratified qq plot')
	explore_parser.add_argument('--qq-n', 
						nargs=0, 
						action=AddTrue, 
						help='print number of markers on qq plot')
	explore_parser.add_argument('--mht', 
						nargs=0, 
						action=AddTrue, 
						help='print manhattan plot')
	explore_parser.add_argument('--color', 
						nargs=0, 
						action=AddTrue, 
						help='plot in color')
	explore_parser.add_argument('--plot-gc', 
						nargs=0, 
						action=AddTrue, 
						help='print manhattan plots with genomic inflation corrected p-values')
	explore_parser.add_argument('--set-gc', 
						action=AddString, 
						type=float, 
						help='set genomic inflation value instead of calculating it')
	explore_parser.add_argument('--pmax', 
						action=AddString, 
						type=float, 
						help='set maximum p-value for top results file (default = 1e-4; will print at least top 100')
	explore_parser.add_argument('--stat', 
						action=AddString, 
						help='string indicating prefix for statistics to be summarized, not including tag (default: STAT=\'marker\')')
	explore_parser.add_argument('--top', 
						action=AddString, 
						type=int, 
						help='an integer; print regional plots for top n regions')
	explore_parser.add_argument('--tag', 
						action=AddString, 
						help='string indicating tag for stats to be summarized, if tag exists (example: TAG=aa and STAT=marker -> aa.marker.p)')
	explore_parser.add_argument('--unrel', 
						nargs=0, 
						action=AddTrue, 
						help='filter based on unrel columns')	
	explore_parser.add_argument('--rsq', 
						action=AddString, 
						type=float, 
						help='threshold for imputation quality (ie. 0.8 filters out markers with r-squared < 0.8)')
	explore_parser.add_argument('--maf', 
						action=AddString, 
						type=float, 
						help='threshold for allele frequency (ie. 0.03 filters out markers with MAF < 0.03)')
	explore_parser.add_argument('--hwe', 
						action=AddString, 
						type=float, 
						help='threshold for Hardy Weinberg p-value (ie. 1e-6 filters out markers with Hardy Weinberg p-value < 1e-6)')
	explore_parser.add_argument('--callrate', 
						action=AddString, 
						type=float, 
						help='threshold for callrate (ie. 0.95 filters out markers with callrate < 0.95)')
	explore_parser.add_argument('--effect', 
						action=AddString, 
						type=float, 
						help='threshold for effect estimate (ie. 1.7 filters out markers with effect estimate > 1.7 and < -1.7)')
	explore_parser.add_argument('--stderr', 
						action=AddString, 
						type=float, 
						help='threshold for standard error (ie. 5 filters out markers with standard error > 5)')
	explore_parser.add_argument('--oddsratio', 
						action=AddString, 
						type=float, 
						help='threshold for odds ratio (ie. 1.3 filters out markers with odds ratio > 1.25 and < 1/1.25 = 0.8)')
	explore_parser.add_argument('--df', 
						action=AddString, 
						type=int, 
						help='threshold for meta analysis degrees of freedom (ie. 4 filters out markers less than 5 datasets included in the meta analysis; requires --meta-dir)')
	explore_parser.add_argument('--sig', 
						action=AddString, 
						type=float, 
						help='line of significance p value (default: 5.4e-8)')
	explore_parser.add_argument('--ext', 
						action=AddString, 
						choices=['tiff','eps','pdf'], 
						help='file type extension for plot files (default: tiff)')
	explore_parser.add_argument('--replace', 
						nargs=0, 
						action=AddTrue, 
						help='replace any existing output files')
	explore_parser_split_group = explore_parser.add_mutually_exclusive_group()
	explore_parser_split_group.add_argument('--region', 
						action=AddString, 
						help='genomic region specified in Tabix format (ie. 1:10583-1010582).')
	explore_parser_split_group.add_argument('--reglist', 
						action=AddString, 
						help='filename for a list of tabix format regions')
	explore_parser.add_argument('--lz-source', 
						action=AddString, 
						help='locuszoom source option')
	explore_parser.add_argument('--lz-build', 
						action=AddString, 
						help='locuszoom build option')
	explore_parser.add_argument('--lz-pop', 
						action=AddString, 
						help='locuszoom pop option')

	##### GC PARSER #####
	gc_parser = subparsers.add_parser('gc', help='apply genomic control to 1 or more p-value columns', parents=[parser])
	gc_required = gc_parser.add_argument_group('required arguments')
	gc_required.add_argument('--out', 
						action=AddString, 
						required=True, 
						help='filename for corrected results (basename only: do not include path or extension)')
	gc_required.add_argument('--data', 
						action=AddString, 
						required=True, 
						help='filename of existing results')
	gc_required.add_argument('--gc', 
						nargs=2, 
						required=True, 
						action=AddString, 
						help='apply genomic control to a 1 or more p-value columns (ex. --gc meta.p 1.0123 --gc meta.aa.p 1.002123)')
	gc_parser.add_argument('--replace', 
						nargs=0, 
						action=AddTrue, 
						help='replace any existing output files')
	gc_parser.add_argument('--qsub', 
						action=AddString, 
						help='string indicating all qsub options to be added to the qsub command (trigger adds jobs to cluster queue')

	##### ANNOT PARSER #####
	annot_parser = subparsers.add_parser('annot', help='annotate variant results using snpEff and SnpSift', parents=[parser])
	annot_required = annot_parser.add_argument_group('required arguments')
	annot_required.add_argument('--file', 
						action=AddString, 
						required=True, 
						help='file name for variant results to be annotated')
	annot_parser.add_argument('--build', 
						action=AddString, 
						help='genomic build (default: GRCh37.75)')
	annot_parser.add_argument('--replace', 
						nargs=0, 
						action=AddTrue, 
						help='replace any existing output files')
	annot_parser.add_argument('--qsub', 
						action=AddString, 
						help='string indicating all qsub options to be added to the qsub command (trigger adds jobs to cluster queue')

	return top_parser
	
def Parse(top_parser):
	args=top_parser.parse_args()
	if 'ordered_args' in args:
		for k in args.ordered_args:
			vars(args).update({k[0]: k[1]})
	else:
		if args.which in ['model','meta','map','compile','explore','gc']:
			top_parser.error("missing argument: no options selected")
	if args.which in ['model']:
		if args.region:
			assert not args.split, top_parser.error("argument -s/--split: not allowed with argument --region")
			assert not args.split_n, top_parser.error("argument -n/--split-n: not allowed with argument --region")
			assert not args.job, top_parser.error("argument -j/--job: not allowed with argument --region")
			assert not args.jobs, top_parser.error("argument --jobs: not allowed with argument --region")
			assert not args.split_chr, top_parser.error("argument --split-chr: not allowed with argument --region")
		if args.reglist:
			assert os.path.exists(args.reglist), top_parser.error("argument --reglist: file does not exist")
		if args.jobs:
			assert os.path.exists(args.jobs), top_parser.error("argument --jobs: file does not exist")
	if args.which == 'map' and not (args.b or args.kb or args.mb or args.n):
		top_parser.error("missing argument: --b, --kb, --mb, or --n required in module map")
	if args.which == 'model' and not (args.fskato is None or args.fskat is None or args.fburden is None) and args.ped is None:
		top_parser.error("missing argument: --ped required for fskato, fskat, or fburden models using data with family structure")
	print ''
	print 'active module: ' + args.which
	return args

def GenerateModelCfg(args):
	config = {'out': None, 'buffer': 100, 'reglist': None, 'region': None,'id': None, 'write_header': False, 'write_eof': False,
					'models': {}, 'model_order': [], 'meta': []}

	##### add top level variables to config
	top_args = [a for a in args if a[0] in ['out','buffer','reglist','region','id']]
	for arg in top_args:
		config[arg[0]] = arg[1]

	# list all possible model level arguments
	model_vars = ['tag','sample','pheno','varlist','fid','iid','focus','ped','sex', 
					'male','female','miss','maf','maxmaf','rsq','hwe','rho','case','ctrl','corstr','sep','lmer_ctrl',
					'reml','lrt','cph_ctrl','skat_wts','burden_wts','skat_method',
					'ggee','bgee','gglm','bglm','glme','blme','cph','neff',
					'fskato','gskato','bskato','fskat','gskat','bskat','fburden','gburden','bburden',
					'oxford','vcf','plink','dos1','dos2']
	if not 'tag' in [a[0] for a in args]:
		args = [('tag', 'NA')] + args
	pre_tag_idx = [a[0] for a in args if a[0] in model_vars].index('tag')

	# extract global model arguments
	model_args_global = dict([a for a in args if a[0] in model_vars][:pre_tag_idx])
	for k in model_args_global.keys():
		if k in ['ggee','bgee','gglm','bglm','glme','blme','cph','neff',
						'fskato','gskato','bskato','fskat','gskat','bskat','fburden','gburden','bburden'] and model_args_global[k] is not None:
			model_args_global['model'] = model_args_global[k]
			model_args_global['model_fxn'] = k
			if k in ['bgee','bglm','blme','bskato','bskat','bburden']:
				model_args_global['family'] = "binomial"
			elif k in ['ggee','gglm','glme','gskato','gskat','gburden']:
				model_args_global['family'] = "gaussian"
			else:
				model_args_global['family'] = None
		elif k in ['oxford','vcf','plink','dos1','dos2'] and model_args_global[k] is not None:
			model_args_global['data'] = model_args_global[k]
			model_args_global['format'] = k
			if not 'varlist' in model_args_global:
				model_args_global['varlist'] = None
			if not 'sample' in model_args_global:
				model_args_global['sample'] = None
		else:
			model_args_global[k] = model_args_global[k]

	# extract local model arguments
	model_args_local = [a for a in args if a[0] in model_vars][pre_tag_idx:]
	local_tag_idx = [a for a, b in enumerate(model_args_local) if b[0] == 'tag']
	if len(local_tag_idx) == 0:
		local_tag_idx = [0]
	local_args = [model_args_local[i:j] for i, j in zip([0]+local_tag_idx[1:], local_tag_idx[1:]+[None])]
	# extract meta arguments
	meta_args = [a for a in args if a[0] == 'meta']

	# loop over model argument sets and add to config['models']
	for l in local_args:
		if l[0][0] != 'tag':
			tag = 'NA'
		else:
			tag = l[0][1]
		config['model_order'].append(tag)
		config['models'][tag] = {'tag': tag}
		config['models'][tag].update(model_args_global)
		for i in xrange(1,len(l)):
			config['models'][tag][l[i][0]] = l[i][1]
			if l[i][0] in ['ggee','bgee','gglm','bglm','glme','blme','cph','neff',
							'fskato','gskato','bskato','fskat','gskat','bskat','fburden','gburden','bburden'] and l[i][1] is not None:
				for k in [x for x in ['ggee','bgee','gglm','bglm','glme','blme','cph','neff',
							'fskato','gskato','bskato','fskat','gskat','bskat','fburden','gburden','bburden'] if x != l[i][0]]:
					if k in config['models'][tag]:
						del config['models'][tag][k]
				config['models'][tag]['model'] = l[i][1]
				config['models'][tag]['model_fxn'] = l[i][0]
				if l[i][0] in ['bgee','bglm','blme','bskato','bskat','bburden']:
					config['models'][tag]['family'] = "binomial"
				elif l[i][0] in ['ggee','gglm','glme','gskato','gskat','gburden']:
					config['models'][tag]['family'] = "gaussian"
				else:
					config['models'][tag]['family'] = None
			elif l[i][0] in ['oxford','vcf','plink','dos1','dos2'] and l[i][1] is not None:
				for k in [x for x in ['oxford','vcf','plink','dos1','dos2'] if x != l[i][0]]:
					if k in config['models'][tag]:
						del config['models'][tag][k]
				config['models'][tag]['data'] = l[i][1]
				config['models'][tag]['format'] = l[i][0]
		if not 'varlist' in config['models'][tag]:
			config['models'][tag]['varlist'] = None
		if not 'sample' in config['models'][tag]:
			config['models'][tag]['sample'] = None

	# loop over meta arguments and add to config['meta']
	for m in meta_args:
		config['meta'].append(m[1])

	# update all defaults and remove any extra settings
	for x in config['models']:
		if config['models'][x]['model_fxn'] in ['ggee','bgee']:
			if 'corstr' in args and config['models'][x]['corstr'] is not None:
				config['models'][x]['corstr'] = key[1]
			else:
				config['models'][x]['corstr'] = 'exchangeable'
		if config['models'][x]['model_fxn'] in ['gskato','bskato','fskato']:
			if not 'rho' in config['models'][x]:
				config['models'][x]['rho'] = 1
		else:
			if 'rho' in config['models'][x]:
				del config['models'][x]['rho']
		if config['models'][x]['model_fxn'] in ['gskato','bskato','fskato','fskat','gskat','bskat']:
			if not 'skat_wts' in config['models'][x]:
				config['models'][x]['skat_wts'] = 'function(maf){dbeta(maf,1,25)}'
			if not 'skat_method' in config['models'][x]:
				config['models'][x]['skat_method'] = 'saddlepoint'
		if config['models'][x]['model_fxn'] in ['gskato','bskato','fskato','fburden','gburden','bburden']:
			if not 'burden_wts' in config['models'][x]:
				config['models'][x]['burden_wts'] = 'function(maf){as.numeric(maf<0.01)}'
		if config['models'][x]['model_fxn'] in ['gskato','bskato','fskato','fburden','gburden','bburden','neff'] and config['region'] is not None:
			if config['id'] is None:
				config['id'] = 'NA'
		if config['models'][x]['model_fxn'] in ['glme','blme']:
			if not 'lmer_ctrl' in config['models'][x]:
				config['models'][x]['lmer_ctrl'] = "check.nobs.vs.rankZ='stop',check.nlev.gtreq.5='stop',check.rankX='stop.deficient',check.scaleX='stop',check.conv.grad=.makeCC('stop',tol=1e-3,relTol=NULL),check.conv.singular=.makeCC(action='stop',tol=1e-4),check.conv.hess=.makeCC(action='stop',tol=1e-6)"
			if not 'lrt' in config['models'][x]:
				config['models'][x]['lrt'] = False
		if config['models'][x]['model_fxn'] == 'glme':
			if not 'reml' in config['models'][x]:
				config['models'][x]['reml'] = False
		if config['models'][x]['model_fxn'] == 'cph':
			if not 'cph_ctrl' in config['models'][x]:
				config['models'][x]['cph_ctrl'] = "eps=1e-09,toler.chol=.Machine$double.eps^0.75,iter.max=20,toler.inf=sqrt(1e-09),outer.max=10"
		if not 'miss' in config['models'][x]:
			config['models'][x]['miss'] = None
		if not 'maf' in config['models'][x]:
			config['models'][x]['maf'] = None
		if not 'maxmaf' in config['models'][x]:
			config['models'][x]['maxmaf'] = None
		if not 'hwe' in config['models'][x]:
			config['models'][x]['hwe'] = None
		if not 'rsq' in config['models'][x]:
			config['models'][x]['rsq'] = None
		if not 'sep' in config['models'][x]:
			config['models'][x]['sep'] = 'tab'
		if not 'case' in config['models'][x]:
			config['models'][x]['case'] = 1
		if not 'ctrl' in config['models'][x]:
			config['models'][x]['ctrl'] = 0
		if not 'sex' in config['models'][x]:
			config['models'][x]['sex'] = None
		if not 'male' in config['models'][x]:
			config['models'][x]['male'] = 1
		if not 'female' in config['models'][x]:
			config['models'][x]['female'] = 2
	return config

def PrintModelOptions(cfg):
	print ''
	print "options in effect ..."
	for k in cfg:
		if not k in ['models','model_order','meta']:
			if cfg[k] is not None and cfg[k] is not False:
				if cfg[k] is True:
					print "      {0:>{1}}".format(str('--' + k.replace('_','-')), len(max(['--' + key.replace('_','-') for key in cfg.keys()],key=len)))
				else:
					print "      {0:>{1}}".format(str('--' + k.replace('_','-')), len(max(['--' + key.replace('_','-') for key in cfg.keys()],key=len))) + " " + str(cfg[k])
	for m in cfg['models']:
		print '   model ' + str(m) + ' ...' if len(cfg['models']) > 1 else '   model ...'
		cfg['models'][m][cfg['models'][m]['model_fxn']] = cfg['models'][m]['model']
		for n in cfg['models'][m]:
			if not n in ['model_fxn','model','family','format','data']:
				if cfg['models'][m][n] is not None and cfg['models'][m][n] is not False:
					if cfg['models'][m][n] is True:
						print "      {0:>{1}}".format(str('--' + n.replace('_','-')), len(max(['--' + key.replace('_','-') for key in cfg['models'][m].keys()],key=len)))
					else:
						print "      {0:>{1}}".format(str('--' + n.replace('_','-')), len(max(['--' + key.replace('_','-') for key in cfg['models'][m].keys()],key=len))) + " " + str(cfg['models'][m][n])
	if len(cfg['meta']) > 0:
		print '   meta analysis ...'
		metas = [(x.split(':')[0],x.split(':')[1]) for x in cfg['meta']]
		for m in metas:
			print "      {0:>{1}}".format(str('--meta ' + m[0]), len(max(['--' + k[0] for k in metas],key=len))) + ":" + str(m[1])
	print ''

def GenerateMetaCfg(args):
	config = {'out': None, 'method': None, 'buffer': 100, 'reglist': None, 'region': None, 'id': None, 'write_header': False, 'write_eof': False,
					'data_info': {}, 'meta_info': {}, 'meta_order': [], 'file_order': []}

	##### add top level variables to config
	top_args = [a for a in args if a[0] in ['out','method','buffer','reglist','region','id']]
	for arg in top_args:
		config[arg[0]] = arg[1]

	# list all possible model level arguments
	model_vars = ['gc','marker_col','freq_col','rsq_col','hwe_col','effect_col','stderr_col','or_col','z_col','p_col','n_col','n','tag','file','maf','rsq','hwe']
	if not 'tag' in [a[0] for a in args]:
		args = [('tag', 'A')] + args
	pre_tag_idx = [a[0] for a in args if a[0] in model_vars].index('tag')

	# extract global model arguments
	model_args_global = dict([a for a in args if a[0] in model_vars][:pre_tag_idx])
	for k in model_args_global.keys():
		model_args_global[k] = model_args_global[k]

	# extract local model arguments
	model_args_local = [a for a in args if a[0] in model_vars][pre_tag_idx:]
	local_tag_idx = [a for a, b in enumerate(model_args_local) if b[0] == 'tag']
	if len(local_tag_idx) == 0:
		local_tag_idx = [0]
	local_args = [model_args_local[i:j] for i, j in zip([0]+local_tag_idx[1:], local_tag_idx[1:]+[None])]
	# extract meta arguments
	meta_args = [a for a in args if a[0] == 'meta']
	for k in meta_args:
		config['meta_info'][k[1].split(':')[0]] = k[1].split(':')[1].split('+')
		config['meta_order'].append(k[1].split(':')[0])

	# loop over model argument sets and add to config['models']
	for l in local_args:
		tag = l[0][1]
		config['file_order'].append(tag)
		config['data_info'][tag] = {'tag': tag}
		config['data_info'][tag].update(model_args_global)
		for i in xrange(1,len(l)):
			config['data_info'][tag][l[i][0]] = l[i][1]
	for tag in config['data_info']:
		for k in ['marker_col','freq_col','rsq_col','hwe_col','effect_col','stderr_col','or_col','z_col','p_col','n_col']:
			if not k in config['data_info'][tag]:
				config['data_info'][tag][k] = None
	return config

def PrintMetaOptions(cfg):
	print ''
	print "options in effect ..."
	for k in cfg:
		if not k in ['file_order','meta_order','meta_info','data_info']:
			if cfg[k] is not None and cfg[k] is not False:
				if cfg[k] is True:
					print "      {0:>{1}}".format(str('--' + k.replace('_','-')), len(max(['--' + key.replace('_','-') for key in cfg.keys()],key=len)))
				else:
					print "      {0:>{1}}".format(str('--' + k.replace('_','-')), len(max(['--' + key.replace('_','-') for key in cfg.keys()],key=len))) + " " + str(cfg[k])
	for m in cfg['data_info']:
		print '   dataset ' + str(m) + ' ...'
		for n in cfg['data_info'][m]:
			if not n in ['model_fxn','model','family','format','data']:
				if cfg['data_info'][m][n] is not None and cfg['data_info'][m][n] is not False:
					if cfg['data_info'][m][n] is True:
						print "      {0:>{1}}".format(str('--' + n.replace('_','-')), len(max(['--' + key.replace('_','-') for key in cfg['data_info'][m].keys()],key=len)))
					else:
						print "      {0:>{1}}".format(str('--' + n.replace('_','-')), len(max(['--' + key.replace('_','-') for key in cfg['data_info'][m].keys()],key=len))) + " " + str(cfg['data_info'][m][n])
	if len(cfg['meta_order']) > 0:
		print '   meta analysis ...'
		for m in cfg['meta_info']:
			print "      {0:>{1}}".format(str('--meta ' + m), len(max(['--' + k for k in cfg['meta_info']],key=len))) + ":" + str('+'.join(cfg['meta_info'][m]))
	print ''

def GenerateExploreCfg(args, ini):
	config = {'out': None, 'data': None, 'qq': False, 'qq_strat': False, 'qq_n': False, 'mht': False, 'color': False, 'plot_gc': False,
				'set_gc': None, 'ext': 'tiff', 'sig': 0.000000054, 'stat': 'marker', 'top': None, 'region': None, 'region_id': None, 
				'reglist': None, 'pmax': 1e-4, 'tag': None, 'unrel': False, 'lz_source': None, 'lz_build': None, 'lz_pop': None, 
				'callrate': None, 'rsq': None, 'maf': None, 'hwe': None, 'effect': None, 'stderr': None, 'odds_ratio': None, 'df': None}
	for arg in args:
		config[arg[0]] = arg[1]
	config['locuszoom'] = ini.get('main','locuszoom')
	return config

def PrintExploreOptions(cfg):
	print ''
	print "options in effect ..."
	for k in cfg:
		if cfg[k] is not None and cfg[k] is not False:
			if cfg[k] is True:
				print "      {0:>{1}}".format(str('--' + k.replace('_','-')), len(max(['--' + key.replace('_','-') for key in cfg.keys()],key=len)))
			else:
				print "      {0:>{1}}".format(str('--' + k.replace('_','-')), len(max(['--' + key.replace('_','-') for key in cfg.keys()],key=len))) + " " + str(cfg[k])
	print ''

def GenerateGcCfg(args, ini):
	config = {'out': None, 'data': None, 'gc': {}}
	for arg in args:
		if arg[0] == 'gc':
			config['gc'][arg[1][0]] = arg[1][1]
		else:
			config[arg[0]] = arg[1]
	return config

def PrintGcOptions(cfg):
	print ''
	print "options in effect ..."
	for k in cfg:
		if cfg[k] is not None and cfg[k] is not False:
			if cfg[k] is True:
				print "      {0:>{1}}".format(str('--' + k.replace('_','-')), len(max(['--' + key.replace('_','-') for key in cfg.keys()],key=len)))
			else:
				print "      {0:>{1}}".format(str('--' + k.replace('_','-')), len(max(['--' + key.replace('_','-') for key in cfg.keys()],key=len))) + " " + str(cfg[k])
	print ''

def GenerateAnnotCfg(args, ini):
	config = {'file': None, 'build': 'GRCh37.75', 'replace': False, 'qsub': None, 'snpeff': None, 'snpsift': None, 'dbnsfp': None}
	for arg in args:
		config[arg[0]] = arg[1]
	config['snpeff'] = ini.get('main','snpeff')
	config['snpsift'] = ini.get('main','snpsift')
	config['dbnsfp'] = ini.get('main','dbnsfp')
	return config

def PrintAnnotOptions(cfg):
	print ''
	print "options in effect ..."
	for k in cfg:
		if cfg[k] is not None and cfg[k] is not False:
			if cfg[k] is True:
				print "      {0:>{1}}".format(str('--' + k.replace('_','-')), len(max(['--' + key.replace('_','-') for key in cfg.keys()],key=len)))
			else:
				print "      {0:>{1}}".format(str('--' + k.replace('_','-')), len(max(['--' + key.replace('_','-') for key in cfg.keys()],key=len))) + " " + str(cfg[k])
	print ''
