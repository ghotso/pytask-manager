import { ReactElement, useRef, useEffect } from 'react';
import Editor, { OnMount } from '@monaco-editor/react';
import { useMantineTheme } from '@mantine/core';
import * as monaco from 'monaco-editor';

interface CodeEditorProps {
  value: string;
  onChange: (value: string) => void;
  height?: number | string;
}

export function CodeEditor({ value, onChange }: CodeEditorProps): ReactElement {
  const editorRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);
  const theme = useMantineTheme();

  const handleEditorDidMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;
    
    // Configure Monaco editor theme
    monaco.editor.defineTheme('pytaskmanager-dark', {
      base: 'vs-dark',
      inherit: true,
      rules: [],
      colors: {
        'editor.background': theme.colors.dark[8],
        'editor.foreground': theme.colors.gray[3],
        'editor.lineHighlightBackground': theme.colors.dark[7],
        'editor.selectionBackground': theme.colors.blue[9] + '40',
        'editorCursor.foreground': theme.colors.blue[4],
        'editorLineNumber.foreground': theme.colors.dark[3],
        'editorLineNumber.activeForeground': theme.colors.gray[5],
      },
    });
    
    monaco.editor.setTheme('pytaskmanager-dark');

    // Set initial height based on content
    updateEditorHeight(editor);

    // Listen for content changes to update height
    editor.onDidContentSizeChange(() => {
      updateEditorHeight(editor);
    });
  };

  const updateEditorHeight = (editor: monaco.editor.IStandaloneCodeEditor) => {
    const contentHeight = Math.max(
      editor.getContentHeight(),
      300 // Minimum height in pixels (about 14 lines)
    );
    editor.layout({ width: editor.getLayoutInfo().width, height: contentHeight });
    const container = editor.getContainerDomNode();
    if (container) {
      container.style.height = `${contentHeight}px`;
    }
  };

  // Handle controlled value updates
  useEffect(() => {
    if (editorRef.current && value !== editorRef.current.getValue()) {
      const editor = editorRef.current;
      const position = editor.getPosition();
      editor.setValue(value);
      if (position) {
        editor.setPosition(position);
      }
      updateEditorHeight(editor);
    }
  }, [value]);

  return (
    <Editor
      height="auto"
      defaultLanguage="python"
      value={value}
      onChange={(newValue) => onChange(newValue || '')}
      onMount={handleEditorDidMount}
      options={{
        minimap: { enabled: false },
        fontSize: 14,
        lineNumbers: 'on',
        roundedSelection: false,
        scrollBeyondLastLine: false,
        automaticLayout: true,
        wordWrap: 'on',
        lineHeight: 21,
        padding: { top: 10, bottom: 10 },
        scrollbar: {
          vertical: 'hidden',
          horizontal: 'hidden',
        },
        fixedOverflowWidgets: true,
        overviewRulerBorder: false,
        overviewRulerLanes: 0,
        hideCursorInOverviewRuler: true,
      }}
    />
  );
} 