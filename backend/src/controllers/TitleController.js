const { execFile } = require('child_process');
const path = require('path');

// Path to your Python script (same folder)
const pythonScriptPath = path.join(__dirname, 'app.py');

// Function to execute the Python script and send input
function executePythonScript(inputTitle) {
    return new Promise((resolve, reject) => {
        const pythonProcess = execFile('python', [pythonScriptPath], (error, stdout, stderr) => {
            if (error) {
                console.error(`exec error: ${error}`);
                reject(`exec error: ${error}`);
                return;
            }

            if (stderr) {
                console.error(`Python stderr: ${stderr}`);
            }

            try {
                const output = JSON.parse(stdout.trim());
                resolve(output);
            } catch (e) {
                console.error('Error parsing Python output:', e);
                reject('Error parsing Python output: ' + e);
            }
        });

        pythonProcess.stdin.write(inputTitle + '\n');
        pythonProcess.stdin.end();
    });
}

// Express.js route handler for checking titles
async function check(req, res) {
    try {
        const { title } = req.query;
        if (!title) {
            return res.status(400).json({ error: 'Title is required' });
        }

        const pythonResult = await executePythonScript(title);
        return res.json({ feedback: pythonResult });
    } catch (error) {
        console.error('Error executing Python script:', error);
        return res.status(500).json({ error: 'An error occurred while processing the title' });
    }
}

module.exports = { check };