#!/usr/bin/env node
'use strict';

function fail(msg) {
  console.error(msg);
  process.exit(1);
}

const inputPath = process.argv[2];
const outputPath = process.argv[3];
if (!inputPath || !outputPath) {
  fail('Usage: node ua-arch-analyze.js <input.json> <output.json>');
}

let input;
try {
  const raw = require('fs').readFileSync(inputPath, 'utf8');
  input = JSON.parse(raw);
} catch (e) {
  fail('Failed to read/parse input JSON: ' + e.message);
}

const fs = require('fs');
const path = require('path');

const fileNodes = input.fileNodes || [];
const importEdges = input.importEdges || [];
const allEdges = input.allEdges || [];

try {
  // ---------- A. Directory Grouping ----------
  const filePaths = fileNodes.map(n => n.filePath || n.name || '');

  function commonPrefix(paths) {
    if (paths.length === 0) return '';
    const split = paths.map(p => p.split('/'));
    let prefix = [];
    const minLen = Math.min(...split.map(s => s.length));
    for (let i = 0; i < minLen - 1; i++) { // -1 so we don't consume entire filename
      const seg = split[0][i];
      if (split.every(s => s[i] === seg)) {
        prefix.push(seg);
      } else {
        break;
      }
    }
    return prefix.length ? prefix.join('/') + '/' : '';
  }

  const prefix = commonPrefix(filePaths);

  function dirGroupFor(filePath) {
    let rest = filePath;
    if (prefix && rest.startsWith(prefix)) {
      rest = rest.slice(prefix.length);
    }
    const parts = rest.split('/');
    if (parts.length > 1) {
      return parts[0];
    }
    // No subdirectory after prefix -- root-level file in this context
    if (prefix) {
      return '(root)';
    }
    // No common prefix at all and no subdirectory -- group by first dir segment of full path
    const fullParts = filePath.split('/');
    if (fullParts.length > 1) return fullParts[0];
    return '(root)';
  }

  const directoryGroups = {};
  const fileIdToGroup = {};
  for (const node of fileNodes) {
    const fp = node.filePath || node.name || '';
    let group = dirGroupFor(fp);
    // Flat-structure fallback: if everything ends up in (root), group by extension/pattern
    directoryGroups[group] = directoryGroups[group] || [];
    directoryGroups[group].push(node.id);
    fileIdToGroup[node.id] = group;
  }

  // Detect flat structure: if only one group and it's (root), regroup by file type pattern
  const groupNames = Object.keys(directoryGroups);
  if (groupNames.length === 1 && groupNames[0] === '(root)') {
    const newGroups = {};
    for (const node of fileNodes) {
      const fp = node.filePath || node.name || '';
      const base = path.basename(fp);
      let g = 'misc';
      if (/\.test\.|\.spec\.|^test_|_test\.|Test\.|_spec\./.test(base)) g = 'test';
      else if (/\.config\.|^config|settings/.test(base)) g = 'config';
      else {
        const ext = path.extname(base).replace('.', '') || 'noext';
        g = ext;
      }
      newGroups[g] = newGroups[g] || [];
      newGroups[g].push(node.id);
      fileIdToGroup[node.id] = g;
    }
    Object.keys(directoryGroups).forEach(k => delete directoryGroups[k]);
    Object.assign(directoryGroups, newGroups);
  }

  // ---------- B. Node Type Grouping ----------
  const nodeTypeGroups = {};
  const idToNode = {};
  for (const node of fileNodes) {
    idToNode[node.id] = node;
    const t = node.type || 'file';
    nodeTypeGroups[t] = nodeTypeGroups[t] || [];
    nodeTypeGroups[t].push(node.id);
  }

  // ---------- C. Import Adjacency Matrix ----------
  const fileFanOut = {};
  const fileFanIn = {};
  for (const node of fileNodes) {
    fileFanOut[node.id] = 0;
    fileFanIn[node.id] = 0;
  }
  const groupImportsTo = {}; // group -> set of groups it imports from
  const groupImportedBy = {}; // group -> set of groups that import it

  for (const e of importEdges) {
    if (fileFanOut.hasOwnProperty(e.source)) fileFanOut[e.source]++;
    if (fileFanIn.hasOwnProperty(e.target)) fileFanIn[e.target]++;

    const sg = fileIdToGroup[e.source];
    const tg = fileIdToGroup[e.target];
    if (sg && tg) {
      groupImportsTo[sg] = groupImportsTo[sg] || new Set();
      groupImportsTo[sg].add(tg);
      groupImportedBy[tg] = groupImportedBy[tg] || new Set();
      groupImportedBy[tg].add(sg);
    }
  }

  const groupImportsToObj = {};
  for (const k in groupImportsTo) groupImportsToObj[k] = Array.from(groupImportsTo[k]);
  const groupImportedByObj = {};
  for (const k in groupImportedBy) groupImportedByObj[k] = Array.from(groupImportedBy[k]);

  // ---------- D. Cross-Category Dependency Analysis ----------
  const crossCategoryMap = {};
  for (const e of allEdges) {
    const sNode = idToNode[e.source];
    const tNode = idToNode[e.target];
    if (!sNode || !tNode) continue;
    if (sNode.type === tNode.type && sNode.type === 'file' && e.type === 'imports') continue; // handled separately, but still count if desired
    const key = `${sNode.type}->${tNode.type}->${e.type}`;
    crossCategoryMap[key] = (crossCategoryMap[key] || 0) + 1;
  }
  const crossCategoryEdges = Object.keys(crossCategoryMap).map(key => {
    const [fromType, rest] = key.split('->');
    const toType = rest;
    const parts = key.split('->');
    return {
      fromType: parts[0],
      toType: parts[1],
      edgeType: parts[2],
      count: crossCategoryMap[key],
    };
  });

  // ---------- E. Inter-Group Import Frequency ----------
  const interGroupMap = {};
  for (const e of importEdges) {
    const sg = fileIdToGroup[e.source];
    const tg = fileIdToGroup[e.target];
    if (!sg || !tg) continue;
    const key = `${sg}=>${tg}`;
    interGroupMap[key] = (interGroupMap[key] || 0) + 1;
  }
  const interGroupImports = Object.keys(interGroupMap).map(key => {
    const [from, to] = key.split('=>');
    return { from, to, count: interGroupMap[key] };
  }).sort((a, b) => b.count - a.count);

  // ---------- F. Intra-Group Import Density ----------
  const intraGroupDensity = {};
  for (const g of Object.keys(directoryGroups)) {
    let internalEdges = 0;
    let totalEdges = 0;
    for (const e of importEdges) {
      const sg = fileIdToGroup[e.source];
      const tg = fileIdToGroup[e.target];
      if (sg !== g && tg !== g) continue;
      totalEdges++;
      if (sg === g && tg === g) internalEdges++;
    }
    intraGroupDensity[g] = {
      internalEdges,
      totalEdges,
      density: totalEdges > 0 ? +(internalEdges / totalEdges).toFixed(3) : 0,
    };
  }

  // ---------- G. Directory Pattern Matching ----------
  const dirPatternTable = [
    [['routes', 'api', 'controllers', 'endpoints', 'handlers'], 'api'],
    [['services', 'core', 'lib', 'domain', 'logic'], 'service'],
    [['models', 'db', 'data', 'persistence', 'repository', 'entities'], 'data'],
    [['components', 'views', 'pages', 'ui', 'layouts', 'screens'], 'ui'],
    [['middleware', 'plugins', 'interceptors', 'guards'], 'middleware'],
    [['utils', 'helpers', 'common', 'shared', 'tools'], 'utility'],
    [['config', 'constants', 'env', 'settings'], 'config'],
    [['__tests__', 'test', 'tests', 'spec', 'specs'], 'test'],
    [['types', 'interfaces', 'schemas', 'contracts', 'dtos'], 'types'],
    [['hooks'], 'hooks'],
    [['store', 'state', 'reducers', 'actions', 'slices'], 'state'],
    [['assets', 'static', 'public'], 'assets'],
    [['migrations'], 'data'],
    [['management', 'commands'], 'config'],
    [['templatetags'], 'utility'],
    [['signals'], 'service'],
    [['serializers'], 'api'],
    [['cmd'], 'entry'],
    [['internal'], 'service'],
    [['pkg'], 'utility'],
    [['workers', 'jobs', 'tasks', 'queue'], 'service'],
    [['bot'], 'api'],
    [['agents', 'pipelines'], 'service'],
    [['storage'], 'data'],
    [['webapp'], 'ui'],
    [['web'], 'ui'],
    [['docs', 'documentation', 'wiki'], 'documentation'],
    [['deploy', 'deployment', 'infra', 'infrastructure'], 'infrastructure'],
    [['.github', '.gitlab', '.circleci'], 'ci-cd'],
    [['k8s', 'kubernetes', 'helm', 'charts'], 'infrastructure'],
    [['terraform', 'tf'], 'infrastructure'],
    [['docker'], 'infrastructure'],
    [['sql', 'database', 'schema'], 'data'],
    [['scripts'], 'utility'],
    [['tests'], 'test'],
  ];

  function matchDirPattern(dirName) {
    const lower = dirName.toLowerCase();
    for (const [names, label] of dirPatternTable) {
      if (names.includes(lower)) return label;
    }
    return null;
  }

  const patternMatches = {};
  for (const g of Object.keys(directoryGroups)) {
    const m = matchDirPattern(g);
    if (m) patternMatches[g] = m;
  }

  // ---------- H. Deployment Topology Detection ----------
  const infraFiles = [];
  let hasDockerfile = false, hasCompose = false, hasK8s = false, hasTerraform = false, hasCI = false;
  for (const node of fileNodes) {
    const fp = node.filePath || '';
    const base = path.basename(fp);
    if (/^Dockerfile/i.test(base)) { hasDockerfile = true; infraFiles.push(fp); }
    if (/docker-compose/i.test(base)) { hasCompose = true; infraFiles.push(fp); }
    if (/\.ya?ml$/i.test(base) && /k8s|kubernetes/i.test(fp)) { hasK8s = true; infraFiles.push(fp); }
    if (/\.tf$|\.tfvars$/i.test(base)) { hasTerraform = true; infraFiles.push(fp); }
    if (/^\.github\/workflows\//.test(fp) || /\.gitlab-ci\.yml$/i.test(base) || /^Jenkinsfile$/i.test(base)) {
      hasCI = true; infraFiles.push(fp);
    }
    if (/^Makefile$/i.test(base)) { infraFiles.push(fp); }
  }

  // ---------- I. Data Pipeline Detection ----------
  const schemaFiles = [];
  const migrationFiles = [];
  const dataModelFiles = [];
  const apiHandlerFiles = [];
  for (const node of fileNodes) {
    const fp = node.filePath || '';
    const base = path.basename(fp).toLowerCase();
    const tags = (node.tags || []).map(t => t.toLowerCase());
    if (/\.sql$/.test(base) || base === 'schema.py' || tags.includes('schema')) schemaFiles.push(node.id);
    if (/migrations\//i.test(fp) || /migration/.test(base)) migrationFiles.push(node.id);
    if (/models?\.py$/.test(base) || /storage\//.test(fp) || tags.includes('model') || tags.includes('persistence')) dataModelFiles.push(node.id);
    if (/bot\//.test(fp) || /handlers?\.py$/.test(base) || tags.includes('handler') || tags.includes('endpoint') || node.type === 'endpoint') apiHandlerFiles.push(node.id);
  }

  // ---------- J. Documentation Coverage ----------
  const docNodes = fileNodes.filter(n => n.type === 'document');
  const groupsWithDocsSet = new Set();
  for (const doc of docNodes) {
    const fp = (doc.filePath || '').toLowerCase();
    for (const g of Object.keys(directoryGroups)) {
      if (fp.includes(g.toLowerCase())) groupsWithDocsSet.add(g);
    }
  }
  const totalGroups = Object.keys(directoryGroups).length;
  const groupsWithDocs = groupsWithDocsSet.size;
  const coverageRatio = totalGroups > 0 ? +(groupsWithDocs / totalGroups).toFixed(3) : 0;
  const undocumentedGroups = Object.keys(directoryGroups).filter(g => !groupsWithDocsSet.has(g));

  // ---------- K. Dependency Direction ----------
  const dependencyDirection = [];
  const seenPairs = new Set();
  for (const item of interGroupImports) {
    const { from, to } = item;
    if (from === to) continue;
    const pairKey = [from, to].sort().join('|');
    if (seenPairs.has(pairKey)) continue;
    seenPairs.add(pairKey);
    const forward = interGroupMap[`${from}=>${to}`] || 0;
    const backward = interGroupMap[`${to}=>${from}`] || 0;
    if (forward === backward) continue;
    if (forward > backward) {
      dependencyDirection.push({ dependent: from, dependsOn: to });
    } else {
      dependencyDirection.push({ dependent: to, dependsOn: from });
    }
  }

  // ---------- File Stats ----------
  const filesPerGroup = {};
  for (const g of Object.keys(directoryGroups)) filesPerGroup[g] = directoryGroups[g].length;
  const nodeTypeCounts = {};
  for (const t of Object.keys(nodeTypeGroups)) nodeTypeCounts[t] = nodeTypeGroups[t].length;

  const result = {
    scriptCompleted: true,
    commonPrefix: prefix,
    directoryGroups,
    nodeTypeGroups,
    crossCategoryEdges,
    interGroupImports,
    intraGroupDensity,
    patternMatches,
    groupImportsTo: groupImportsToObj,
    groupImportedBy: groupImportedByObj,
    deploymentTopology: {
      hasDockerfile,
      hasCompose,
      hasK8s,
      hasTerraform,
      hasCI,
      infraFiles: Array.from(new Set(infraFiles)),
    },
    dataPipeline: {
      schemaFiles,
      migrationFiles,
      dataModelFiles,
      apiHandlerFiles,
    },
    docCoverage: {
      groupsWithDocs,
      totalGroups,
      coverageRatio,
      undocumentedGroups,
    },
    dependencyDirection,
    fileStats: {
      totalFileNodes: fileNodes.length,
      filesPerGroup,
      nodeTypeCounts,
    },
    fileFanIn,
    fileFanOut,
  };

  fs.writeFileSync(outputPath, JSON.stringify(result, null, 2));
  process.exit(0);
} catch (e) {
  fail('Fatal error during analysis: ' + (e && e.stack ? e.stack : e));
}
