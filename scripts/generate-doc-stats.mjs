import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const walk = (dir) => fs.readdirSync(dir, {withFileTypes: true}).flatMap((entry) =>
  entry.isDirectory() ? walk(path.join(dir, entry.name)) : [path.join(dir, entry.name)]);
const documents = walk(path.join(root, 'docs')).filter((file) => /\.mdx?$/.test(file));
const models = JSON.parse(fs.readFileSync(path.join(root, 'src/data/models.json'), 'utf8'));
const validationPath = path.join(root, 'src/data/modelValidationResults.json');
const validation = fs.existsSync(validationPath)
  ? JSON.parse(fs.readFileSync(validationPath, 'utf8'))
  : {schemaVersion: 1, environments: [], runs: []};
const modelIds = new Set(models.filter(model => model.kind !== 'resource').map(model => model.id));
const runs = validation.runs.filter(run => modelIds.has(run.modelId));
const passed = runs.filter(run => run.status === 'passed');
const environments = new Map(validation.environments.map(environment => [environment.id, environment]));
const summaries = {};
// Customer pages and catalog use curated effect records; diagnostic history stays private.
for (const run of runs) {
  if (!summaries[run.modelId] || run.date >= summaries[run.modelId].date) {
    summaries[run.modelId] = {
      id: run.id,
      status: run.status,
      level: run.level,
      date: run.date,
      revision: run.revision,
      environment: environments.get(run.environmentId)?.label ?? run.environmentId,
      summary: run.summary,
    };
  }
}
const output = path.join(root, 'src/data/siteStats.json');
const content = JSON.stringify({
  documents: documents.length,
  models: models.filter(model => model.kind !== 'resource').length,
  resources: models.filter(model => model.kind === 'resource').length,
  repositories: models.length,
  modelGroups: new Set(models.filter(model => model.kind !== 'resource').map((model) => model.group)).size,
  hardwareValidatedInThisEdition: new Set(passed.map(run => run.modelId)).size,
  hardwareBasicValidatedInThisEdition: new Set(passed.filter(run => run.level === 'basic').map(run => run.modelId)).size,
  hardwareCorrectnessValidatedInThisEdition: new Set(passed.filter(run => run.level === 'correctness').map(run => run.modelId)).size,
  modelsWithValidationRecords: new Set(runs.map(run => run.modelId)).size,
  validationRuns: runs.length,
  modelValidationSummaries: summaries,
}, null, 2) + '\n';
if (!fs.existsSync(output) || fs.readFileSync(output, 'utf8') !== content) {
  const temporary = `${output}.${process.pid}.tmp`;
  fs.writeFileSync(temporary, content, {flag: 'wx'});
  try {
    fs.renameSync(temporary, output);
  } finally {
    if (fs.existsSync(temporary)) fs.unlinkSync(temporary);
  }
}
