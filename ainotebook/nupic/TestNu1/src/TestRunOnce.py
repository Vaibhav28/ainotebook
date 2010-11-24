#!/usr/bin/env python

#####################################################################
# Test Run Once 
#####################################################################
# Tested with python 2.5.4

from nupic.network.helpers import  \
    AddSensor, AddClassifierNode,  \
    AddZeta1Level, TrainBasicNetwork, RunBasicNetwork

from nupic.network import CreateRuntimeNetwork, Network
from nupic.analysis import InferenceAnalysis, responses

from nupic.analysis import netexplorer
import random

#####################################################################
# Init Data 
#####################################################################
        
# Data generation parameters 
useCoherentData            = True       # If False, there will be no temporal
                                        # coherence in the training data
numSequencesPerBitwormType = 10         # No. of sequences for each bitworm type
sequenceLength             = 20         # No. of patterns in each temporal sequence
inputSize                  = 16         # Size of input vector
additiveNoiseTraining      = 0.0        # Range of noise added or subtracted
                                        # from training data
bitFlipProbabilityTraining = 0.0        # Prob. of switching a bit in training data
trainingMinLength          = 9          # Shortest bitworm used for training
trainingMaxLength          = 12         # Longest bitworm used for training
additiveNoiseTesting       = 0.0        # Range of noise added or subtracted
                                        # from test data
bitFlipProbabilityTesting  = 0.0        # Prob. of switching a bit in test data
testMinLength              = 5          # Shortest bitworm used for testing
testMaxLength              = 8          # Longest bitworm used for testing

# Learning parameters
maxDistance                = 0.0
topNeighbors               = 3
transitionMemory           = 4

# Various file names
untrainedNetwork   = "untrained_bitworm.xml"    # Name of the untrained network
trainedNetwork     = "trained_bitworm.xml"      # Name of the trained network
trainingFile       = "training_data.txt"        # Location of training data
trainingCategories = "training_categories.txt"  # Location of training categories
trainingResults    = "training_results.txt"     # File containing inference
                                                # results for each training pattern
testFile           = "test_data.txt"            # Location of test data
testCategories     = "test_categories.txt"      # Location of test categories
testResults        = "test_results.txt"         # File containing inference
                                                # results for each test pattern
reportFile         = "report.txt"               # File containing overall results
                                                # generated by generateReport()

#####################################################################
# Bit Worm Data
#####################################################################
class BitwormData(netexplorer.DataInterface):
      
    def __init__(self):
        """ Initialize parameters to default values."""
        netexplorer.DataInterface.__init__(self)
        self.addParam('inputSize', default=16) 
        self.addParam('numSequencesPerBitwormType', default=10)
        self.addParam('sequenceLength', default=20)
        self.addParam('minLength', default=5)
        self.addParam('maxLength', default=8)
        self.addParam('randomSeed', default=41)
        self.addParam('additiveNoise', default=0.0)
        self.addParam('bitFlipProbability', default=0.0)
        self.inputs = []
        self.categories = []  # will be 0 for solid, 1 for textured

    def createBitworm(self, wormType, pos, length, inputSize):
        """ Create a single bitworm of the given type, position, and length.
        Stores the data in self.inputs and the category in self.categories."""
        input = []
        for _ in range(0, pos): input.append(self.getBit(0))
        if wormType == 'solid':
            self.categories.append(0)
            for _ in range (pos, pos+length): input.append(self.getBit(1))        
        elif wormType == 'textured':
            self.categories.append(1)
            bit = 1
            for _ in range (pos, pos+length):
                input.append(self.getBit(bit))
                bit = 1 - bit
                        
        for _ in range (pos+length, inputSize): input.append(self.getBit(0))
        self.inputs.append(input)
    
    def appendBlank(self):
        """ Append a blank vector."""
        size = self['inputSize']
        blank = []
        for _ in range(0,size): blank.append(0)
        self.inputs.append(blank)
        self.categories.append(0)
        
    def createDataNoTemporalCorrelation(self):
        """ Create a set of patterns that have no temporal relationship.
        Creates a total of numSequencesPerWormType*2 patterns."""
        size = self['inputSize']
        random.seed(self['randomSeed'])
        for _ in range(0, self['numSequencesPerBitwormType']):
          for wormType in ['solid','textured']:
            length = random.randint(self['minLength'], self['maxLength'])
            pos = random.randint(0, size-length-1)
            self.createBitworm(wormType, pos, length, size)
        self.writeFiles()
      
    def createData(self):
        """ Generate the data using the current set of parameters
        and write them out to files. For each sequence, this code
        generates a bitworm using a random length and position (within the current
        parameter constraints), and then slides it left and right."""
        
        size = self['inputSize']
        random.seed(self['randomSeed'])
        for _ in range(0, self['numSequencesPerBitwormType']):
            increment = 1
            for wormType in ['solid','textured']:
                length = random.randint(self['minLength'], self['maxLength'])
                pos = random.randint(0, size-length-1)
                increment = -1*increment
                for _ in range(0, self['sequenceLength']):
                    self.createBitworm(wormType, pos, length, size)
                    if pos+length >= size:
                        increment = -1*increment
                    if pos + increment < 0: increment = -1*increment
                    pos += increment
                              
                self.appendBlank()
            
        self.writeFiles()

    def writeFiles(self):
        """Write the generated data into files."""
        # Ensure vector data and category data have the same length
        if len(self.inputs) != len(self.categories):
          raise "Data and category vectors don't match"
        
        # write out data vectors    
        dataFile = open(self['prefix']+'data.txt', 'w')
        for input in self.inputs:
          for x in input: print >>dataFile, x,
          print >> dataFile
    
        # write out category file
        catFile = open(self['prefix']+'categories.txt', 'w')
        for c in self.categories: print >> catFile, c
        catFile.close()
        dataFile.close()
        
        print len(self.inputs), "data vectors written to ",self['prefix']+'data.txt'

    def getBit(self, originalBit):
        """ Adds noise to originalBit (additive or bitFlip) and returns it."""
        bit = originalBit
        if random.uniform(0,1) < self['bitFlipProbability']: bit = 1 - bit
        bit += random.uniform(-self['additiveNoise'], self['additiveNoise'])
        
        if bit==0 or bit==1: return int(bit)
        else: return bit
                
#########
# End of class
#########    

def generateBitwormData(additiveNoiseTraining = 0.0, bitFlipProbabilityTraining= 0.0,
                        additiveNoiseTesting = 0.0, bitFlipProbabilityTesting= 0.0,
                        numSequencesPerBitwormType = 10, sequenceLength = 20,
                        inputSize = 16,
                        trainingMinLength = 9, trainingMaxLength = 12,
                        testMinLength = 5, testMaxLength = 8):
    """ Generate bitworm training and test data files. Return the input size,
    the number of training vectors, and the number of test vectors."""
    
    # Generate training data with worms of lengths between 5 and 8
    trainingData = BitwormData()
    trainingData['prefix'] = 'training_'
    trainingData['minLength'] = trainingMinLength
    trainingData['maxLength'] = trainingMaxLength
    trainingData['sequenceLength'] = sequenceLength
    trainingData['inputSize'] = inputSize
    trainingData['numSequencesPerBitwormType'] = numSequencesPerBitwormType
    trainingData['additiveNoise'] = additiveNoiseTraining
    trainingData['bitFlipProbability'] = bitFlipProbabilityTraining
    trainingData.createData()

    # Generate test data containing different worms, with lengths between 9 and 12
    testData = BitwormData()
    testData['prefix'] = 'test_'
    testData['minLength'] = testMinLength
    testData['maxLength'] = testMaxLength
    testData['numSequencesPerBitwormType'] = numSequencesPerBitwormType
    testData['randomSeed'] = trainingData['randomSeed'] + 1
    testData['additiveNoise'] = additiveNoiseTesting
    testData['bitFlipProbability'] = bitFlipProbabilityTesting
    testData.createData()    
    return [trainingData['inputSize'], len(trainingData.inputs), len(testData.inputs)]
 
def generateIncoherentBitwormData():
    
    """ Generate bitworm training and test data files. Here we ensure the
    training data files have no temporal relationship. The test set is the
    same as in generateBitwormData."""
    # Generate training data with bitworms of lengths between 5 and 8
    trainingData = BitwormData()
    trainingData['prefix'] = 'training_'
    trainingData['minLength'] = 9
    trainingData['maxLength'] = 12
    trainingData['numSequencesPerBitwormType'] = 200
    trainingData.createDataNoTemporalCorrelation()
    
    # Generate test data containing different bitworms, with lengths
    # between 9 and 12
    testData = BitwormData()
    testData['prefix'] = 'test_'
    testData['minLength'] = 5
    testData['maxLength'] = 8
    testData['numSequencesPerBitwormType'] = 200
    testData['randomSeed'] = trainingData['randomSeed'] + 1
    testData.createDataNoTemporalCorrelation()    
    return [trainingData['inputSize'], len(trainingData.inputs), len(testData.inputs)]

def generateReport(trainedNetwork, trainingResults, trainingCategories, testResults, testCategories, reportFile):

    # Open report file
    file = open(reportFile, 'w')
    
    #--------------------------------------------------------
    # Initialize the network we will use
    runtimeNet = CreateRuntimeNetwork(trainedNetwork)
    
    #--------------------------------------------------------
    # Display some general statistics about the trained network
    print >>file, "------------------------------\n"
    print >>file, "General network statistics:"
    nodes = runtimeNet.getElementNames()
    print >>file, "Network has ", len(nodes), "nodes."
    print >>file,"Node names are:"
    for nodeName in sorted(nodes):
        print >>file, "   ", nodeName
      
    print >>file, "\n"
    
    if "Level1" in nodes:
        level1 = runtimeNet['Level1']
        skipLines = 1
    elif "level1" in nodes:
        level1 = runtimeNet['level1[0]']
        skipLines = 0
      
    if "Level2" in nodes:
        level2 = runtimeNet['Level2']
    elif 'topNode' in nodes:
        level2 = runtimeNet['topNode']
    
    nc = responses.GetNumCoincidences(level1)
    ng = responses.GetNumGroups(level1)
    print >>file, "Node Level1 has", nc, "coincidences and", ng, "groups."
    nc = responses.GetNumCoincidences(level2)
    print >>file, "Node Level2 has", nc, "coincidences."
    
    #--------------------------------------------------------
    # Report training results
    print >>file, "------------------------------\n"
    print >>file, "Performance statistics:"
    print >>file, "Comparing: ", trainingResults, " with ",trainingCategories
    r = computePerformance(trainingResults, trainingCategories, skipLines)
    print >>file, "Performance on training set: %.2f%%, %d correct out of %d vectors\n" % (100.0*r[0]/r[1],r[0],r[1])
    
    # Report test results
    print >>file, "Comparing: ", testResults, " with ",testCategories
    r = computePerformance(testResults, testCategories, skipLines)
    print >>file, "Performance on test set: %.2f%%, %d correct out of %d vectors\n" % (100.0*r[0]/r[1],r[0],r[1])
    
    #--------------------------------------------------------
    # Report coincidence matrix and group structure
    print >>file, "------------------------------\n"
    print >>file, "Getting groups and coincidences from the node Level1 in network '",trainedNetwork
    Wd = responses.GetCoincidences(level1).toDense()
    groups = responses.GetGroups(level1)
    # Get each group
    for gindx, gg in enumerate(groups):
      print >>file, "\n====> Group = ", gindx
      # For each group, get each coincidence index
      for cd in sorted(gg):
        # For each coincidence, print out each element
        for e in Wd[cd]:
          if e==0 or e==1: print >>file, int(e),
          else: print >>file, e,
        print >>file, ""
      
    #--------------------------------------------------------
    # Report coincidence matrix for top node
    Wd = responses.GetCoincidences(level2).toDense()
    activeOutputs = level1['activeOutputCount']
    print >>file, "\nFull set of Level 2 coincidences: "
    for i, cd in enumerate(Wd):
      print >>file, i, "->", cd[0:activeOutputs]
    
    #--------------------------------------------------------
    # Cleanup bundle
    runtimeNet.cleanupBundleWhenDone()

def computePerformance(resultsFile, categoriesFile, skipLines = 1):
    """ Compute the performance when comparing a results file against a category file.
    Returns a list of the number correct, the total number of vectors, and a list
    of all results lines that did not match. Ignore the first line of the
    results file."""
    
    resultLines = file(resultsFile).readlines()
    report = InferenceAnalysis(
      resultsFilename=resultsFile,
      categoryFileFormat = 2,
      categoryFilename=categoriesFile,
      resultColumns=2, skipLines=skipLines)
    mismatches = [resultLines[i+1] for i in report.errors]
    return [report.nCorrect, report.nKnown, mismatches]


#####################################################################
# Run Application
#####################################################################
def runApp():
    
    print "Running Test Program"
        
     # Generate and write bitworm data into the default files train_* and test_*
    if useCoherentData:
        dataParameters = generateBitwormData(
                            additiveNoiseTraining      = additiveNoiseTraining,
                            bitFlipProbabilityTraining = bitFlipProbabilityTraining,
                            additiveNoiseTesting       = additiveNoiseTesting,
                            bitFlipProbabilityTesting  = bitFlipProbabilityTesting,
                            numSequencesPerBitwormType = numSequencesPerBitwormType,
                            sequenceLength             = sequenceLength,
                            inputSize                  = inputSize,
                            trainingMinLength          = trainingMinLength,
                            trainingMaxLength          = trainingMaxLength,
                            testMinLength              = testMinLength,
                            testMaxLength              = testMaxLength)
    else:
        dataParameters = generateIncoherentBitwormData()
    
    print "Data Parameters:"
    print dataParameters
    
    # Create the bitworm network.
    bitNet = Network()
    AddSensor(bitNet, featureVectorLength = inputSize)
    AddZeta1Level(bitNet, numNodes = 1)
    AddClassifierNode(bitNet, numCategories = 2)
    
    # Set some of the parameters we are interested in tuning
    bitNet['level1'].setParameter('topNeighbors',topNeighbors)
    bitNet['level1'].setParameter('maxDistance',maxDistance)
    bitNet['level1'].setParameter('transitionMemory', transitionMemory)
    bitNet['topNode'].setParameter('spatialPoolerAlgorithm','dot')

    # Train the network
    bitNet = TrainBasicNetwork(bitNet,
                dataFiles     = [trainingFile],
                categoryFiles = [trainingCategories])

    # Ensure the network learned the training set
    accuracy = RunBasicNetwork(bitNet,
                dataFiles     = [trainingFile],
                categoryFiles = [trainingCategories],
                resultsFile   = trainingResults)
    print "Training set accuracy with HTM = ", accuracy*100.0

    # Run inference on test set to check generalization
    accuracy = RunBasicNetwork(bitNet,
                dataFiles     = [testFile],
                categoryFiles = [testCategories],
                resultsFile   = testResults)
    print "Test set accuracy with HTM = ", accuracy*100.0
    
    # Save the trained network
    bitNet.save(trainedNetwork)

    # Write out a report of the overall network progress
    generateReport(trainedNetwork, trainingResults, trainingCategories,
                   testResults, testCategories, reportFile)
    
    print "Bitworm run complete. Detailed results are in 'report.txt'"
            
#####################################################################
# Main 
#####################################################################
if __name__ == '__main__':
    runApp()

#########
# End of Class
#########
    