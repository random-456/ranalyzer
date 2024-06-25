import os
import sys

# Configuration
output_file = "flattened_project.txt"
excluded_files = ["flattener.py", ".env", ".gitignore", "requirements.txt", "workflow"]
excluded_folders = [".git"]

def write_file_content(file_path, relative_path):
    with open(output_file, "a", encoding="utf-8") as out_file:
        out_file.write(f"########## {relative_path} ##########\n\n")
        try:
            with open(file_path, "r", encoding="utf-8") as in_file:
                out_file.write(in_file.read())
            out_file.write("\n\n")
        except Exception as e:
            out_file.write(f"Error reading file: {str(e)}\n\n")

def flatten_directory(directory, parent_path=""):
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        relative_path = os.path.join(parent_path, item)

        if os.path.isfile(item_path) and item not in excluded_files:
            write_file_content(item_path, relative_path)
        elif os.path.isdir(item_path) and item not in excluded_folders:
            flatten_directory(item_path, relative_path)

def main():
    # Clear or create the output file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("")

    # Get the directory of the script
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

    # Change to the script's directory
    os.chdir(script_dir)

    # Flatten the directory
    flatten_directory(".")

    print(f"Flattening completed. Output is available in {output_file}")

if __name__ == "__main__":
    main()