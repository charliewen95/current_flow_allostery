def betweenness():
    parser=argparse.ArgumentParser(description="Loads the specified GB interaction network and calculates the corresponding flow betweenness network")
    
    parser.add_argument(
        '-indir','--inputDirectory',default='.',dest='inDir',
        help='Path to the directory containing the interaction network file. Defaults to currently active directory'
    )
    parser.add_argument(
        '-i', '--interactionFileName',
        help='Name of the GB interaction energy data file to load (required). This data file should contain a'+\
             '\nsingle interaction network. If there are more networks / interactions present, you will need to'+\
             '\nuse the "-selectionQueryStrings" argument to specify a pandas.DataFrame.query search query string'+\
             '\nthat can select a single network from the data. If duplicate edges are present, the program'+\
             '\nwill crash or give unpredictable results'
    )
    
    parser.add_argument(
        '-q','--selectionQueryStrings',nargs='*',
        help='List of query strings to select entries from the interaction data that specify a single network'+\
             '\nto be analyzed. If multiple strings are provided, the results are concatenated using pd.concat'
    )
    parser.add_argument(
        '-c','--NodeColumns',default=['Resid_1','Resid_2'],dest='nodeColumns',nargs='*',
        help='Names of the columns containing the names of the interacting nodes for each interaction entry'+\
             '\nexactly two arguments should be given. If not only the first two entries will get used.'
    )
    parser.add_argument(
        '-e','--energyColumn',default='TOTAL',
        help='Name of the column containing the energy values of each interaction used to compute betweenness weights'
    )
    parser.add_argument(
        '-s','--sourceNodeNames',nargs='+',dest='sourceNodeNames',
        help='string to be fed to the pandas DataFrame.query function to collect a list of source node names'+\
             '\nif multiple entries are given, each will be fed and the results aggregated into a list of'+\
             '\nof unique node names'
    )
    parser.add_argument(
        '-t','--targetNodeNames',nargs='+',dest='targetNodeNames',
        help='string to be fed to the pandas DataFrame.query function to collect a list of target node names'+\
             '\nif multiple entries are given, each will be fed and the results aggregated into a list of'+\
             '\nof unique node names. Note: if there is any overlap. I.e. sourceNodes and targetNodes litst'+\
             '\ncontain some of the same node(s) then a warning will be thrown and the common nodes will be put'+\
             '\ninto the source node list.'
    )
    
    parser.add_argument(
        '-outdir','--outputFileDirectory',default='.',dest='outDir',
        help='Path of the directory to write output files to'
    )
    parser.add_argument(
        '-o','--outputFileNameBase',
        help='Base of the filenames e.g. edge betweenness would be in "outputFileNameBase.EdgeBetweenness.csv" (required)'
    )
    parser.add_argument(
        '-ft','--writeFullTable',nargs='?',default=False,const=True,
        help='If this flag is set, the output table will contain all data from each row of the input dataframe'+\
             'otherwise it will only contain the node columns and betweenness column'
    )
    parser.add_argument(
        '-wnvec','--writeNodeVector',nargs='?',const=True,default=False,
        help='If flag is given, node betweenness will also be computed written to "outputFileNameBase.NodeBetweenness.csv"'
    )
    
    
    parser.add_argument(
        '-windmap','--writeMatrixIndexToNodeNameMap',nargs='?',const=True,default=False,
        help='If this flag is given, a data frame containging the columns "MatInd" and "NodeName" is written to'+\
             '\n"outputFileNameBase.IndToNameMap.csv"'
    )
    
    parser.add_argument(
        '-dryrun',nargs='?',const=True,default=False,
        help='Dont run anything, jsut print out input argument namespace and end program'
    )
    
    parser.add_argument(
        '-v','--verbose',nargs='?',const=True,default=False,
        help='controls printing of progress / information to stdout during run'
    )
    parser.add_argument(
        '-vl','--verboseLevel',default=0,
        help='when verbose flag is given, controls the amount of detail printed'
    )
    
    args=parser.parse_args()
    
    if args.verbose or args.dryrun:
        print('Input arguments:',args)
    if not args.dryrun:
        verbose=args.verbose
        verboseLevel=int(args.verboseLevel)
        outFileBase=args.outputFileNameBase
        inputFile=args.inDir+'/'+args.interactionFileName
        if verbose:
            print('loading data',end='\n' if args.verboseLevel==0 else ",")
        tempData=pd.read_csv(inputFile)
        if (not (args.selectionQueryStrings is None)) and len(args.selectionQueryStrings) > 0:
            if verbose and (verboseLevel > 0):
                print('-filtering loaded data')
            interactionData=pd.concat([
                tempData.query(selectionQuery).copy() \
                for selectionQuery in args.selectionQueryStrings
            ])
            tempData=[]
        else:
            interactionData=tempData.copy()
            tempData=[]
        
        nodeColumn_1,nodeColumn_2=args.nodeColumns
        if verbose and (verboseLevel > 0):
            print('Building node name to index maps')
        nodeNames=np.unique(np.sort(np.concatenate([
                interactionData[nodeColumn_1].unique(),
                interactionData[nodeColumn_2].unique()])))
        nameToIndTable=pd.DataFrame({
            'NodeNames':np.array(nodeNames,dtype=str),
            'NodeInds':np.arange(len(nodeNames))
        })
        if args.writeMatrixIndexToNodeNameMap:
            if verbose and (verboseLevel>0):
                print('saving node name indexing map')
            nameToIndTable.to_csv(
                args.outDir+'/'+outFileBase+'.IndToNameMap.csv',
                index=False
            )
        
        if verbose and (verboseLevel > 1):
            print(interactionData.head())
            
        if verbose and (verboseLevel>0):
            print('building source node list')
        sourceNodeNames=np.array(args.sourceNodeNames)
        sourceNodes=np.array([
            nameToIndTable.set_index('NodeNames')['NodeInds'].loc[sourceNodeName] \
            for sourceNodeName in sourceNodeNames
        ])
        if verbose and (verboseLevel>1):
            print('source nodes:')
            print(pd.DataFrame({'NodeNames':sourceNodes,'MatrixIndices':sourceNodes}))
        
        if verbose and (verboseLevel>0):
            print('building target node list')
        targetNodeNames=np.array(args.targetNodeNames)
        targetNodes=np.array([
            nameToIndTable.set_index('NodeNames')['NodeInds'].loc[targetNodeName] \
            for targetNodeName in targetNodeNames
        ])
        if verbose and (verboseLevel>1):
            print('target nodes:')
            print(pd.DataFrame({'NodeNames':targetNodeNames,'MatrixIndices':targetNodes}))
                  
        if verbose:
            print('Constructing network matrix')
        netMat=np.array(sp.sparse.coo_matrix(
            (interactionData[args.energyColumn].abs(),
             (nameToIndTable.set_index('NodeNames')['NodeInds'].loc[interactionData[nodeColumn_1].map(str)],
              nameToIndTable.set_index('NodeNames')['NodeInds'].loc[interactionData[nodeColumn_2].map(str)])),
            shape=(len(nameToIndTable),len(nameToIndTable))
        ).todense())
        
        btwMat=np.array(corr_utils.getBtwMat(
            mat=netMat,sources=sourceNodes,targets=targetNodes,
            verbose=verbose,verboseLevel=verboseLevel,
            useProgressBar=False,useLegacyAlgorithm=False
        ))
        
        if verbose:
            print('Compiling betweenness table')
        btwTable=pd.DataFrame({
            nodeColumn_1:interactionData[nodeColumn_1],
            nodeColumn_2:interactionData[nodeColumn_2],
            'Betweenness':btwMat[(
                nameToIndTable.set_index('NodeNames')['NodeInds'].loc[
                    interactionData[nodeColumn_1].map(str)],
                nameToIndTable.set_index('NodeNames')['NodeInds'].loc[
                    interactionData[nodeColumn_2].map(str)]
            )]
        })
        
        if args.writeFullTable:
            if verbose:
                print('Joining Betweenness data to interaction data')
            btwTable=btwTable.set_index([nodeColumn_1,nodeColumn_2]).join(
                other=interactionData.set_index([nodeColumn_1,nodeColumn_2]),
                how='right')
        
        if verbose:
            print('Saving betweenness data')
        btwTable.to_csv(args.outDir+'/'+args.outputFileNameBase+'.EdgeBetweenness.csv',index=False)
        
        if args.writeNodeVector:
            if verbose:
                print('Computing node betweenness')
            nodeBtw=np.sum(btwMat,axis=1)/2.
            nodeTable=pd.DataFrame({
                'NodeName':nameToIndTable['NodeNames'],
                'Betweenness':nodeBtw[nameToIndTable['NodeInds']]
            })
            if verbose:
                print('Saving node betweenness data')
            nodeTable.to_csv(args.outDir+'/'+args.outputFileNameBase+'.NodeBetweenness.csv',index=False)
