// The caller selects a local copy of the parser used by Logseq Desktop 0.10.15.
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const readline = require("node:readline");

try {
  const selected = process.argv[2];
  const file = selected ? require.resolve(path.resolve(selected)) : require.resolve("mldoc", {paths: [process.cwd()]});
  const sha = crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
  if (sha !== "6929ff314ac52750bf9b9da6212465f6614875ae2bf03fe53514dac3cce55659") {
    throw new Error("Select the unmodified mldoc 1.5.7 index.js.");
  }
  const parser = require(file).Mldoc;
  process.stdout.write(JSON.stringify({ready: true, version: "1.5.7", sha256: sha}) + "\n");
  const input = readline.createInterface({input: process.stdin, crlfDelay: Infinity});
  input.on("line", line => {
    try {
      const {format, text} = JSON.parse(line);
      const config = {format, toc: false, heading_number: false, keep_line_break: true, heading_to_list: false};
      const ast = JSON.parse(parser.parseJson(text, JSON.stringify(config)));
      process.stdout.write(JSON.stringify({ast}) + "\n");
    } catch (error) {
      process.stdout.write(JSON.stringify({error: error.message}) + "\n");
    }
  });
} catch (error) {
  process.stdout.write(JSON.stringify({error: "Select mldoc 1.5.7 with --mldoc: " + error.message.split("\n")[0]}) + "\n");
  process.exitCode = 1;
}
