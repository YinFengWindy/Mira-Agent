// Isolate the real desktop runtime before its module resolves the user's home directory.
const { app } = require("electron");
if (!process.env.SHIORI_QA_HOME) throw new Error("SHIORI_QA_HOME is required");
app.setPath("home", process.env.SHIORI_QA_HOME);
import("../../dist/main.js");
