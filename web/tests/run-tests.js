#!/usr/bin/env node
/**
 * Test runner for the web port.
 *
 * The browser sources are plain classic scripts that share one global scope
 * and deliberately have no module system, so the runner rebuilds that same
 * environment in a Node vm context and then executes the test file in it.
 *
 * Usage:  node web/tests/run-tests.js
 */

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const jsDir = path.join(__dirname, "..", "js");
const sources = ["automaton.js", "algorithms.js", "examples.js"];

const context = vm.createContext({ console: console, JSON: JSON, Math: Math });

for (const file of sources) {
  const fullPath = path.join(jsDir, file);
  vm.runInContext(fs.readFileSync(fullPath, "utf8"), context, { filename: fullPath });
}

const testFile = path.join(__dirname, "algorithms.test.js");
vm.runInContext(fs.readFileSync(testFile, "utf8"), context, { filename: testFile });

const failures = vm.runInContext("globalThis.__TEST_FAILURES__", context);
process.exit(failures === 0 ? 0 : 1);
