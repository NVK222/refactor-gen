import * as vscode from 'vscode';
import axios from 'axios';

interface GenerateResponse { generated_code: string; }
interface RefactorResponse { refactored_code: string; }


export function activate(context: vscode.ExtensionContext) {
    const backendUrl = "http://localhost:8000";

    let generateCode = vscode.commands.registerCommand('refactor-gen.generate', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {return;}

        const selection = editor.selection;
        const lineText = editor.document.lineAt(selection.start.line).text;

        await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: "RefactorGen is thinking...",
            cancellable: false
        }, async () => {
            try {
                const response = await axios.post<GenerateResponse>(`${backendUrl}/generate`, {
                    prompt: lineText,
                    language: editor.document.languageId
                });


                await editor.edit(editBuilder => {
                    editBuilder.insert(editor.selection.end, "\n");
                    editBuilder.insert(editor.selection.active, response.data.generated_code)
                });
            } catch (err) {
                vscode.window.showErrorMessage("Connection to AI Backend failed.");
            }
        });
    });

    let refactorCode = vscode.commands.registerCommand('refactor-gen.refactor', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor || editor.selection.isEmpty) {
            vscode.window.showWarningMessage("Select code to refactor first.");
            return;
        }

        const selection = editor.selection;
        const originalCode = editor.document.getText(selection);

        await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: "RefactorGen is refactoring...",
            cancellable: false
        }, async () => {
            try {
                const response = await axios.post<RefactorResponse>(`${backendUrl}/refactor`, {
                    code: originalCode,
                    instruction: "Improve readability and performance"
                });

                const refactoredCode = response.data.refactored_code;
                showDiffWebview(context, editor, selection, originalCode, refactoredCode);
            } catch (err) {
                vscode.window.showErrorMessage("Refactor request failed.");
            }
        });
    });

    context.subscriptions.push(generateCode, refactorCode);
}

function showDiffWebview(context: vscode.ExtensionContext, editor: vscode.TextEditor, selection: vscode.Selection, oldCode: string, newCode: string) {
    const panel = vscode.window.createWebviewPanel('refactorDiff', 'Refactor Preview', vscode.ViewColumn.Beside, { enableScripts: true });

    panel.webview.html = `
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: var(--vscode-font-family); padding: 20px; color: var(--vscode-foreground); background: var(--vscode-editor-background); }
                .diff-container { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
                pre { background: rgba(0,0,0,0.2); padding: 10px; border-radius: 4px; overflow: auto; white-space: pre-wrap; }
                .header { font-weight: bold; margin-bottom: 10px; opacity: 0.8; }
                button { background: var(--vscode-button-background); color: var(--vscode-button-foreground); border: none; padding: 8px 16px; cursor: pointer; border-radius: 2px; }
                button:hover { background: var(--vscode-button-hoverBackground); }
                .actions { margin-top: 20px; }
            </style>
        </head>
        <body>
            <h3>Review Changes</h3>
            <div class="diff-container">
                <div><div class="header">Original</div><pre>${escapeHtml(oldCode)}</pre></div>
                <div><div class="header">Refactored</div><pre>${escapeHtml(newCode)}</pre></div>
            </div>
            <div class="actions">
                <button onclick="accept()">Accept Changes</button>
            </div>
            <script>
                const vscode = acquireVsCodeApi();
                function accept() { vscode.postMessage({ command: 'accept' }); }
            </script>
        </body>
        </html>
    `;

    panel.webview.onDidReceiveMessage(message => {
        if (message.command === 'accept') {
            editor.edit(edit => edit.replace(selection, newCode));
            panel.dispose();
        }
    });
}

function escapeHtml(text: string) {
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

export function deactivate() { }
