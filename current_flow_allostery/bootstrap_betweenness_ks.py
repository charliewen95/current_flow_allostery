try:
    import argparse
except ImportError:
    raise ImportError("require argparse")

#numerical / data packages
try:
    import numpy as np
    np.set_printoptions(threshold=10)
except ImportError:
    raise ImportError("require numpy")
try:
    import pandas as pd
except ImportError:
    raise ImportError("require pandas")
try:
    import scipy
    import scipy.sparse
    import scipy as sp
    import scipy.stats
except ImportError:
    raise ImportError("require scipy (NOTE: check scipy submodules)")

#utilities
import sys
import gc
import time

##others


#self defined functions
if __name__ == "__main__":
    from functions import database_mod as db_m
else:
    from .functions import database_mod as db_m

if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=
        "Loads the specified GB interaction network and calculates the corresponding flow betweenness network")
    
    parser.add_argument(
        '-dbp','--databasePath',dest='databasePath',
        help='Path to the directory containing the interaction network file. (required)'
    )
    
    parser.add_argument(
         '-odbp','--outputDatabase',default=None,
        help='This parameter controls the path of the database that will be used for output'+\
             'By default, the database being read from will also be written to for output.'
    )
    
    parser.add_argument(
         '-qs','--querySQL',default='SELECT *; FROM Networks',
         dest='querySQL',
        help='SQL string to load the edge data from the database.'+\
             '\nDefaluts to "SELECT *; FROM Networks" to select all data from'+\
             'the "Networks" table'
    )
    parser.add_argument(
        '-sgc','--systemGroupColumn',default='system',
        dest='systemGroupColumn',
        help='Name of the column used to group different systems to be tested.'+\
             '\nIf this occurs over multiple columns in the database, those columns'+\
             '\nwill need to be merged into a single column using the "querySQL" query'+\
             '\nand then the appropriate merged name(s) entered here.'+\
             '\nE.g. if you have a system and variant column and your reference "system"'+\
             '\nis defined as system="wt" and variant="standard", and you also need the'+\
             '\nSeqid_1,Seqid_2,Chain_Delta, and Betweenness columns for grouping / testing.'+\
             '\nthen you would use:'+\
             '\n --querySQL "SELECT system||variant AS System,Seqid_1,Seqid_2,Chain_Delta,Betweenness'+\
             '\n             FROM Networks"'+\
             '\n -sgc System -referenceSystems wtstandard. Default is "system"'
    )
    parser.add_argument(
        '-igc','--interactionGroupColumns',nargs='*',
        default=['Seqid_1','Seqid_2','Chain_Delta'],
        dest='interactionGroupColumns',
        help='Names of columns used to group individual interactions to test.'+\
             '\nDefault is "Seqid_1" "Seqid_2" "Chain_Delta"'
    )
    parser.add_argument(
        '-rs','--referenceSystems',nargs='*',
        default=['wt2'],dest='referenceSystems',
        help='List of systems to use as reference systems.'+\
             '\nThe test systems will then be the set of all other systems.'
             '\nBootstrapping is performed over all pairs of reference and test systems'+\
             '\nunless the "testAllPairs" flag is set, in which case this parameter does nothing.'+\
             '\nDefault is "wt2"'
    )
    parser.add_argument(
        '-vc','--valueColumn',default='Betweenness',dest='valueColumn',
        help='Name of the column containing the values describing the distributions to be tested.'
    )
    parser.add_argument(
        '-al','--alphas',nargs='*',default=[.1],dest='alphas',
        help='List of alpha values to be considered (where alpha = 1 - confidence level).'+\
             '\n(Note: the minimum alpha value determines the number of bootstrap samples'+\
             '\nbased on 1/(alpha/2)^2, with a minimum of 64 bootstrap samples regardless'+\
             '\nof the minimum alpha. So setting alpha smaller will require more time and memory)'
    )
    parser.add_argument(
        '-tap','--testAllPairs',nargs='?',default=False,const=True,
        dest='testAllPairs',
        help='If this flag is set, all pairs of systems will be tested. (not yet implemented)'
    )
    
    parser.add_argument(
        '-obn','--outputBase',default='Edge_Betweenness_KS',
        dest='outputBase',
        help='Base name for tables to be added to the database. If the "outputToCSV" flag'+\
             '\nis set, then this will serve as the base name of the csv datafiles instead.'+\
             '\nDefault is "Edge_Betweenness_KS". If writting to csv files, '+\
             '\nthis base name should include the entire path to where you want to save the files'
    )
    
    parser.add_argument(
        '-ocf','--outputToCSV',nargs='?',default=False,const=True,
        dest='outputToCSV',
        help='If set, csv files will be written instead of adding tables to the database'
    )
    
    parser.add_argument(
        '-wbd','--writeBootstrapDistributions',nargs='?',default=False,const=True,
        dest='writeBootstrapDistributions',
        help='If this flag is set the KS value distributions generated by bootstrapping'+\
             'will be written to tables (or csv files if the "outputToCSV" flag is set)'
    )
    
    parser.add_argument(
        '-fgc','--flushGroupCount',default=1,dest='flushGroupCount',
        help='Number of interaction groups to run before writting output.'+\
             '\nUseful for tunning performance. Generally, total time spent'+\
             '\nwritting will be lower when more groups are flushed at once,'+\
             '\nespecially when output is being written to a database'
    )
    
    parser.add_argument(
        '-dryrun',nargs='?',const=True,default=False,dest='dryrun',
        help='Dont run anything, jsut print out input argument namespace and end program'
    )
    
    parser.add_argument(
        '-v','--verbose',nargs='?',const=True,default=False,dest='verbose',
        help='controls printing of progress / information to stdout during run'
    )
    parser.add_argument(
        '-vl','--verboseLevel',default=0,dest='verboseLevel',
        help='when verbose flag is given, controls the amount of detail printed'+\
             '0: Only write basic progress messages'+\
             '\n1: Also show timing and progress percentages'+\
             '\n2: Write additional detail, such as input arguments and data statistics / headers'+\
             '\n3: Echo back all sql commands being run'
    )
    
    args=parser.parse_args()
    
    if args.verbose or args.dryrun:
        print('Input arguments:',args)
    if not args.dryrun:
        verbose=args.verbose
        verboseLevel=int(args.verboseLevel)
        
        if verbose and verboseLevel>0:
            ti=time.time()
            
        if not args.outputDatabase is None:
            outputDatabase=args.outputDatabase
        else:
            outputDatabase=args.databasePath
        
        if verbose:
            print("Starting up")
        #transcribe input arguments to variables
        databasePath=args.databasePath
        outputBase=args.outputBase
        writeBootstrapDistributions=args.writeBootstrapDistributions
        outputToCSV=args.outputToCSV
        interactionGroupColumns=args.interactionGroupColumns
        systemGroupColumn=args.systemGroupColumn
        referenceSystems=args.referenceSystems
        querySQL=args.querySQL
        flushGroupCount=int(args.flushGroupCount)
        valueColumn=args.valueColumn
        alphas=np.sort(np.unique(np.array(list(map(float,args.alphas)))))
    
#        ### This code adapted from ###
#        ### https://writeonly.wordpress.com/2009/07/16/simple-read-only-sqlalchemy-sessions/
#        ### used to ensure input SQL query string will effectively not have write access
#        def abort_ro(*args,**kwargs):
#            ''' the terrible consequences for trying 
#                to flush to the db '''
#            print("No writing allowed, tsk!  We're telling mom!")
#            return 
#        
#        def db_setup(connstring='sqlite:///'+databasePath,
#                     readOnly=True,echo=(verbose and (verboseLevel > 2))):
#            engine = create_engine(connstring, echo=echo)
#            Session = sessionmaker(
#                bind=engine, 
#                autoflush=not readOnly, 
#                autocommit=not readOnly
#            )
#            session = Session()
#            
#            if readOnly:
#                session.flush = abort_ro   # now it won't flush!
#    
#            return session, engine
#        ### ### ###
#        
#        readSession, readEngine=db_setup()
#        if not (args.outputDatabase is None):
#            writeSession, writeEngine = db_setup(
#                connstring='sqlite:///'+outputDatabase,readOnly=False)
#        else:
#            writeSession,writeEngine=db_setup(readOnly=False)
   
        ##### 
        connstring='sqlite:///'+databasePath
        
        echo=( verbose and (verboseLevel > 2))
         
        alphas=np.sort(np.unique(np.array(list(alphas))))
        readSession, readEngine= db_m.db_setup(connstring,True,echo)
        if not (outputDatabase is None):
            connstring='sqlite:///'+outputDatabase
            writeSession, writeEngine = db_m.db_setup(
                connstring,False,echo)
        else:
            writeSession,writeEngine= db_m.db_setup(connstring,False,echo)
        #####        
        
        if verbose:
            print("Loading data using input SQL query")
            sys.stdout.flush()
            if verboseLevel>0:
                t1=time.time()
        
        query = readSession.query(querySQL)
        networkData = pd.read_sql(query.statement,readEngine)
        if len(networkData)==0:
            print('Input query yielded no data! Exiting')
        else:
            if verbose:
                if verboseLevel>0:
                    t2=time.time()
                    print('-Input data query time: %.2f seconds'%(t2-t1))
                    t1=time.time()
                    if verboseLevel>1:
                        print('-- Data Extracted From Query --')
                        print(networkData.head())
                        print(networkData.describe())
                        print('-- -- --')
                print('Splitting Reference and Test System Data')
                sys.stdout.flush()
            
            refData=networkData[
                networkData[systemGroupColumn].isin(referenceSystems)
            ]
            testData=networkData[
                networkData[systemGroupColumn].isin(referenceSystems).map(lambda x: not x)
            ]
            if verbose:
                if (verboseLevel>0):
                    t2=time.time()
                    print('-Splitting time: %.2f seconds'%(t2-t1))
                    if verboseLevel>1:
                        print('--- reference data ---')
                        print(refData.head())
                        print(refData.describe())
                        print('\n--- Test Data ---')
                        print(testData.head())
                        print(testData.describe())
                print("--- --- Running Bootstrapping --- ---")
                refSystemGroups=refData.groupby(systemGroupColumn)
                testSystemGroups=testData.groupby(systemGroupColumn)
                for refSystemGroup in refSystemGroups:
                    refSystemName,refSystemData=refSystemGroup
                    for testSystemGroup in testSystemGroups:
                        testSystemName,testSystemData=testSystemGroup
                        if verbose:
                            print('--- Testing',refSystemName,'vs',testSystemName,'---')
                        interactionGroups=refSystemData.groupby(interactionGroupColumns)
                        
                        resultTables=[]
                        bootstrapTables=[]
                        for iGroup,interactionGroup in enumerate(interactionGroups):
                            interactionName,refInteractionData=interactionGroup
                            interactionQuery=' and '.join([
                                "({colname} == {colval})".format(
                                    colname=cname,colval=cval
                                ) \
                                for cname,cval in zip(interactionGroupColumns,interactionName)
                            ])
                            if verbose:
                                print('-Testing: ',interactionQuery,end=": ")
                                if verboseLevel>0:
                                    t1=time.time()
                                sys.stdout.flush()
                            testInteractionData=testSystemData.query(interactionQuery)
                            refVals=np.array(refInteractionData[valueColumn])
                            testVals=np.array(testInteractionData[valueColumn])
                            jointVals=np.concatenate([refVals,testVals])
                            
                            nBootSamples=int(np.max([64,1./(np.min(alphas)/2.)**2]))
                            if verbose:
                                print('Bootstrapping Null',end=', ')
                                sys.stdout.flush()
                            nullBootData=np.zeros(nBootSamples)
                            for iBoot in np.arange(nBootSamples):
                                nullBootData[iBoot]=sp.stats.ks_2samp(
                                    np.random.choice(a=jointVals,size=len(jointVals),replace=True),
                                    jointVals
                                ).statistic
                            if verbose:
                                print('Ref',end=', ')
                                sys.stdout.flush()
                            refBootData=np.zeros(nBootSamples)
                            for iBoot in np.arange(nBootSamples):
                                refBootData[iBoot]=sp.stats.ks_2samp(
                                    np.random.choice(a=refVals,size=len(refVals),replace=True),
                                    jointVals
                                ).statistic
                            if verbose:
                                print('Test',end='; ')
                                sys.stdout.flush()
                            testBootData=np.zeros(nBootSamples)
                            for iBoot in np.arange(nBootSamples):
                                testBootData[iBoot]=sp.stats.ks_2samp(
                                    np.random.choice(a=testVals,size=len(testVals),replace=True),
                                    jointVals
                                ).statistic
                            
                            if writeBootstrapDistributions:
                                if verbose:
                                    print('Compiling Bootstrap Data Table',end="; ")
                                    sys.stdout.flush()
                                bootDataFrame=pd.DataFrame({
                                    'Null_KS':nullBootData,
                                    'Reference_KS':refBootData,
                                    'Test_KS':testBootData
                                })
                                bootDataFrame['Reference_'+systemGroupColumn]=refSystemName
                                bootDataFrame['Test_'+systemGroupColumn]=testSystemName
                                for gColName,gColVal in zip(interactionGroupColumns,interactionName):
                                    bootDataFrame[gColName]=gColVal
                                bootstrapTables.append(bootDataFrame.copy())
                                if (len(bootstrapTables)>=flushGroupCount) or \
                                   (iGroup == (len(interactionGroups)-1)):
                                    bootDataFrame=pd.concat(bootstrapTables)
                                    if verbose:
                                        print('Flushing Bootstrap Data',end='; ')
                                        sys.stdout.flush()
                                    if outputToCSV:
                                        bootDataFrame.to_csv(
                                            outputBase+'_Bootstrap_Data.csv')
                                    else:
                                        bootDataFrame.to_sql(
                                            outputBase+'_Bootstrap_Data',
                                            con=writeEngine,if_exists='append'
                                        )
                                    bootstrapTables=[]
                                    gc.collect()
                            
                            if verbose:
                                print('Compiling Results Table',end="; ")
                                sys.stdout.flush()
                            resultsFrame=pd.DataFrame({
                                'Alpha':alphas,
                                'nullCut':[
                                    np.quantile(nullBootData,q=1.-alpha/2.) \
                                    for alpha in alphas
                                ],
                                'refCut':[
                                    np.quantile(refBootData,q=alpha/2.) \
                                    for alpha in alphas
                                ],
                                'testCut':[
                                    np.quantile(testBootData,q=alpha/2.) \
                                    for alpha in alphas
                                ]
                            })
                            resultsFrame['Ref_Differs']=resultsFrame['refCut']>resultsFrame['nullCut']
                            resultsFrame['Test_Differs']=resultsFrame['testCut']>resultsFrame['nullCut']
                            resultsFrame['Reference_'+systemGroupColumn]=refSystemName
                            resultsFrame['Test_'+systemGroupColumn]=testSystemName
                            for gColName,gColVal in zip(interactionGroupColumns,interactionName):
                                resultsFrame[gColName]=gColVal
                            resultTables.append(resultsFrame.copy())
                            if (len(resultTables)>=flushGroupCount) or \
                               (iGroup == (len(interactionGroups)-1)):
                                if verbose:
                                    print('Flushing Results Tables',end=';')
                                    sys.stdout.flush()
                                resultsFrame=pd.concat(resultTables)
                                if outputToCSV:
                                    resultsFrame.to_csv(
                                        outputBase+'_Results.csv'
                                    )
                                else:
                                    resultsFrame.to_sql(
                                        outputBase+'_Results',
                                        con=writeEngine,if_exists='append'
                                    )
                                resultTables=[]
                                gc.collect()
                            
                            if verbose:
                                if verboseLevel>0:
                                    t2=time.time()
                                    print(' time=%.2f s'%(t2-t1),end="")
                                print("")
                                sys.stdout.flush()
                            gc.collect()
        if verbose and verboseLevel>0:
            tf=time.time()
            print('--- --- --- --- ---')
            print('Total Run Time: %.4f minutes'%((tf-ti)/60.))
    
###########################

def bootstrap_betweenness(databasePath,outputDatabase=None,querySQL='SELECT *; FROM Networks',systemGroupColumn='system',interactionGroupColumns=['Seqid_1','Seqid_2','Chain_Delta'],referenceSystems=['wt2'],valueColumn='Betweenness',alphas=[.1],testAllPairs=False,outputBase='Edge_Betweenness_KS',outputToCSV=False,writeBootstrapDistributions=False,flushGroupCount=1,dryrun=False,verbose=True,verboseLevel=0):
    """
    Default
    -------
    databasePath				INPUT MUST BE GIVEN
    ouputDatabase 				databasePath
    querySQL      				'SELECT *; FROM Networks'
    systemGroupColumn				'system'
    interactionGroupColumns			['Seqid_1','Seqid_2','Chain_Delta']
    referenceSystems				['wt2']
    valueColumn					'Betweenness'
    alphas					[.1]
    testAllPairs				False
    outputBase					'Edge_Betweenness_KS'
    outputToCSV					False
    writeBootstrapDistributions			False
    flushGroupCount				1
    dryrun					False
    verbose					False
    verboseLevel				0

    Example
    -------
    current_flow_allostery.bootstrap_betweenness(\
    'output_2/GB_Network.db',\
    'output_3/GB_Betweenness_Bootstrapped_KS.db',\
    querySQL='SELECT * FROM Networks WHERE (Seqid_1={1})',\
    alphas=[0.05, 0.1, 0.15],\
    writeBootstrapDistributions=True,\
    flushGroupCount=25,\
    verboseLevel=2\
    )

    Other notes
    -----------
    
    """
    if databasePath == None:
        print('Path to the directory containing the interaction network file. (required)')
    if outputDatabase == None:
        outputDatabase = databasePath

    ##### Start of code 
    if verbose or dryrun:
        print('Input arguments:',databasePath,outputDatabase,querySQL,systemGroupColumn,interactionGroupColumns,referenceSystems,valueColumn,alphas,testAllPairs,outputBase,outputToCSV,writeBootstrapDistributions,flushGroupCount,dryrun,verbose,verboseLevel)
    if not dryrun:
        if verbose and verboseLevel>0:
            ti=time.time()
        if verbose:
            print("Starting up")
        ##### 
        connstring='sqlite:///'+databasePath
        
        echo=( verbose and (verboseLevel > 2))
         
        alphas=np.sort(np.unique(np.array(list(alphas))))
        readSession, readEngine= db_m.db_setup(connstring,True,echo)
        if not (outputDatabase is None):
            connstring='sqlite:///'+outputDatabase
            writeSession, writeEngine = db_m.db_setup(
                connstring,False,echo)
        else:
            writeSession,writeEngine= db_m.db_setup(connstring,False,echo)
        #####        
        if verbose:
            print("Loading data using input SQL query")
            sys.stdout.flush()
            if verboseLevel>0:
                t1=time.time()
        
        networkData = pd.read_sql(querySQL,readEngine)
        if len(networkData)==0:
            print('Input query yielded no data! Exiting')
        else:
            if verbose:
                if verboseLevel>0:
                    t2=time.time()
                    print('-Input data query time: %.2f seconds'%(t2-t1))
                    t1=time.time()
                    if verboseLevel>1:
                        print('-- Data Extracted From Query --')
                        print(networkData.head())
                        print(networkData.describe())
                        print('-- -- --')
                print('Splitting Reference and Test System Data')
                sys.stdout.flush()
            
            refData=networkData[
                networkData[systemGroupColumn].isin(referenceSystems)
            ]
            testData=networkData[
                networkData[systemGroupColumn].isin(referenceSystems).map(lambda x: not x)
            ]
            if verbose:
                if (verboseLevel>0):
                    t2=time.time()
                    print('-Splitting time: %.2f seconds'%(t2-t1))
                    if verboseLevel>1:
                        print('--- reference data ---')
                        print(refData.head())
                        print(refData.describe())
                        print('\n--- Test Data ---')
                        print(testData.head())
                        print(testData.describe())
                print("--- --- Running Bootstrapping --- ---")
                refSystemGroups=refData.groupby(systemGroupColumn)
                testSystemGroups=testData.groupby(systemGroupColumn)
                for refSystemGroup in refSystemGroups:
                    refSystemName,refSystemData=refSystemGroup
                    for testSystemGroup in testSystemGroups:
                        testSystemName,testSystemData=testSystemGroup
                        if verbose:
                            print('--- Testing',refSystemName,'vs',testSystemName,'---')
                        interactionGroups=refSystemData.groupby(interactionGroupColumns)
                        
                        resultTables=[]
                        bootstrapTables=[]
                        for iGroup,interactionGroup in enumerate(interactionGroups):
                            interactionName,refInteractionData=interactionGroup
                            interactionQuery=' and '.join([
                                "({colname} == {colval})".format(
                                    colname=cname,colval=cval
                                ) \
                                for cname,cval in zip(interactionGroupColumns,interactionName)
                            ])
                            if verbose:
                                print('-Testing: ',interactionQuery,end=": ")
                                if verboseLevel>0:
                                    t1=time.time()
                                sys.stdout.flush()
                            testInteractionData=testSystemData.query(interactionQuery)
                            refVals=np.array(refInteractionData[valueColumn])
                            testVals=np.array(testInteractionData[valueColumn])
                            jointVals=np.concatenate([refVals,testVals])
                            
                            nBootSamples=int(np.max([64,1./(np.min(alphas)/2.)**2]))
                            if verbose:
                                print('Bootstrapping Null',end=', ')
                                sys.stdout.flush()
                            nullBootData=np.zeros(nBootSamples)
                            for iBoot in np.arange(nBootSamples):
                                nullBootData[iBoot]=sp.stats.ks_2samp(
                                    np.random.choice(a=jointVals,size=len(jointVals),replace=True),
                                    jointVals
                                ).statistic
                            if verbose:
                                print('Ref',end=', ')
                                sys.stdout.flush()
                            refBootData=np.zeros(nBootSamples)
                            for iBoot in np.arange(nBootSamples):
                                refBootData[iBoot]=sp.stats.ks_2samp(
                                    np.random.choice(a=refVals,size=len(refVals),replace=True),
                                    jointVals
                                ).statistic
                            if verbose:
                                print('Test',end='; ')
                                sys.stdout.flush()
                            testBootData=np.zeros(nBootSamples)
                            for iBoot in np.arange(nBootSamples):
                                testBootData[iBoot]=sp.stats.ks_2samp(
                                    np.random.choice(a=testVals,size=len(testVals),replace=True),
                                    jointVals
                                ).statistic
                            
                            if writeBootstrapDistributions:
                                if verbose:
                                    print('Compiling Bootstrap Data Table',end="; ")
                                    sys.stdout.flush()
                                bootDataFrame=pd.DataFrame({
                                    'Null_KS':nullBootData,
                                    'Reference_KS':refBootData,
                                    'Test_KS':testBootData
                                })
                                bootDataFrame['Reference_'+systemGroupColumn]=refSystemName
                                bootDataFrame['Test_'+systemGroupColumn]=testSystemName
                                for gColName,gColVal in zip(interactionGroupColumns,interactionName):
                                    bootDataFrame[gColName]=gColVal
                                bootstrapTables.append(bootDataFrame.copy())
                                if (len(bootstrapTables)>=flushGroupCount) or \
                                   (iGroup == (len(interactionGroups)-1)):
                                    bootDataFrame=pd.concat(bootstrapTables)
                                    if verbose:
                                        print('Flushing Bootstrap Data',end='; ')
                                        sys.stdout.flush()
                                    if outputToCSV:
                                        bootDataFrame.to_csv(
                                            outputBase+'_Bootstrap_Data.csv')
                                    else:
                                        bootDataFrame.to_sql(
                                            outputBase+'_Bootstrap_Data',
                                            con=writeEngine,if_exists='append'
                                        )
                                    bootstrapTables=[]
                                    gc.collect()
                            
                            if verbose:
                                print('Compiling Results Table',end="; ")
                                sys.stdout.flush()
                            resultsFrame=pd.DataFrame({
                                'Alpha':alphas,
                                'nullCut':[
                                    np.quantile(nullBootData,q=1.-alpha/2.) \
                                    for alpha in alphas
                                ],
                                'refCut':[
                                    np.quantile(refBootData,q=alpha/2.) \
                                    for alpha in alphas
                                ],
                                'testCut':[
                                    np.quantile(testBootData,q=alpha/2.) \
                                    for alpha in alphas
                                ]
                            })
                            resultsFrame['Ref_Differs']=resultsFrame['refCut']>resultsFrame['nullCut']
                            resultsFrame['Test_Differs']=resultsFrame['testCut']>resultsFrame['nullCut']
                            resultsFrame['Reference_'+systemGroupColumn]=refSystemName
                            resultsFrame['Test_'+systemGroupColumn]=testSystemName
                            for gColName,gColVal in zip(interactionGroupColumns,interactionName):
                                resultsFrame[gColName]=gColVal
                            resultTables.append(resultsFrame.copy())
                            if (len(resultTables)>=flushGroupCount) or \
                               (iGroup == (len(interactionGroups)-1)):
                                if verbose:
                                    print('Flushing Results Tables',end=';')
                                    sys.stdout.flush()
                                resultsFrame=pd.concat(resultTables)
                                if outputToCSV:
                                    resultsFrame.to_csv(
                                        outputBase+'_Results.csv'
                                    )
                                else:
                                    resultsFrame.to_sql(
                                        outputBase+'_Results',
                                        con=writeEngine,if_exists='append'
                                    )
                                resultTables=[]
                                gc.collect()
                            
                            if verbose:
                                if verboseLevel>0:
                                    t2=time.time()
                                    print(' time=%.2f s'%(t2-t1),end="")
                                print("")
                                sys.stdout.flush()
                            gc.collect()
        if verbose and verboseLevel>0:
            tf=time.time()
            print('--- --- --- --- ---')
            print('Total Run Time: %.4f minutes'%((tf-ti)/60.))
