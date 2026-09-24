import {downloadArtifact} from '@electron/get';
console.log(await downloadArtifact({version:'44.4.3',artifactName:'electron',platform:'win32',arch:'x64'}));
