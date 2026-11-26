using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

namespace AzurPromiliaSwitcherLauncher
{
    static class Program
    {
        [STAThread]
        static void Main(string[] args)
        {
            string baseDir = AppDomain.CurrentDomain.BaseDirectory;
            string mainPy = Path.Combine(baseDir, "main.py");
            if (!File.Exists(mainPy))
            {
                MessageBox.Show(
                    "未找到 main.py，请确认 AzurPromiliaSwitcher.exe 位于项目根目录。",
                    "启动失败",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
                return;
            }

            string pythonExe = ResolvePython(baseDir);
            if (string.IsNullOrEmpty(pythonExe))
            {
                MessageBox.Show(
                    "未找到可用的 Python 环境（需要 Python 3.11+ 与 PySide6-Fluent-Widgets）。",
                    "启动失败",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
                return;
            }

            string joinedArgs = args.Length > 0 ? " " + string.Join(" ", args) : "";
            var psi = new ProcessStartInfo
            {
                FileName = pythonExe,
                Arguments = "\"" + mainPy + "\"" + joinedArgs,
                WorkingDirectory = baseDir,
                UseShellExecute = false,
                CreateNoWindow = true
            };

            try
            {
                Process.Start(psi);
            }
            catch (Exception ex)
            {
                MessageBox.Show("启动失败: " + ex.Message, "错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private static string ResolvePython(string baseDir)
        {
            string[] candidates = new string[]
            {
                Path.Combine(baseDir, ".venv", "Scripts", "pythonw.exe"),
                Path.Combine(baseDir, ".venv", "Scripts", "python.exe"),
                Path.GetFullPath(Path.Combine(baseDir, "..", "Anime Game Automation Tools", ".venv", "Scripts", "pythonw.exe")),
                Path.GetFullPath(Path.Combine(baseDir, "..", "Anime Game Automation Tools", ".venv", "Scripts", "python.exe"))
            };

            foreach (string path in candidates)
            {
                if (File.Exists(path))
                    return path;
            }
            return "pythonw.exe";
        }
    }
}
