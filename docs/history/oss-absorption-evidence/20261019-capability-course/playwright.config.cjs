const path=require('node:path');
module.exports={testDir:__dirname,testMatch:'audit.spec.cjs',fullyParallel:false,workers:1,retries:0,timeout:90000,outputDir:path.join(process.env.PILOT_OUT,'test-results'),reporter:[['line'],['json',{outputFile:path.join(process.env.PILOT_OUT,'test-results.json')}]]};
