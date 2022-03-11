#!/bin/bash
#SBATCH -J cx26btw
#SBATCH --get-user-env
#SBATCH --partition=defq
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=12
#SBATCH --time=300:00:00

export PATH=/cm/shared/apps\:$PATH
inputDir=GB_Network_Data
outputDir=GB_BTW_Network_Data

which python
python --version

parallel -j 12 "echo working on {3};python flowNetwork/betweenness.py -indir {1} -outdir {2} -i {3}.csv -o {3}.Betweenness -windmap -s `seq -s ' ' 14 226 1356` -t `seq -s ' ' 47 226 1356` -c 'Resid_1' 'Resid_2' -v -vl 2 --writeNodeVector -ft > {2}/{3}.log" ::: $inputDir ::: $outputDir ::: `ls $inputDir | sed "s/.csv//g"`

parallel -j 12 "python <<-EOF
import flowNetwork
flowNetwork.betweenness(\
'{1}',\
'{2}',\
'{3}.csv',\
'{3}.Betweenness',\
None,\
['Resid_1','Resid_2'],\
None,\
['14','240','466','692','918','1144'],\
['47','273','499','725','951','1177'],\
True,\
True,\
True,\
None,\
True,\
2\
)
EOF" ::: $inputDir ::: 'output' ::: `ls $inputDir | sed "s/.csv//g"`

#python <<-EOF
#import flowNetwork
#flowNetwork.betweenness(\
#'GB_Network_Data',\
#'output',\
#'EnergyData_Network.System__n14y2_acetyl.Replica__rep1.Frame__001.csv',\
#'EnergyData_Network.System__n14y2_acetyl.Replica__rep1.Frame__001.Betweenness.csv',\
#None,\
#['Resid_1','Resid_2'],\
#None,\
#['14','240','466','692','918','1144'],\
#['47','273','499','725','951','1177'],\
#True,\
#True,\
#True,\
#None,\
#True,\
#2\
#)
#EOF

#python <<-EOF
#import flowNetwork
#flowNetwork.betweenness('GB_Network_Data','output','EnergyData_Network.System__n14y2_acetyl.Replica__rep1.Frame__001.csv','EnergyData_Network.System__n14y2_acetyl.Replica__rep1.Frame__001.Betweenness.csv',None,['Resid_1','Resid_2'],None,'14 226 1356','47 226 1356',True,True,True,None,True,2)
#EOF

