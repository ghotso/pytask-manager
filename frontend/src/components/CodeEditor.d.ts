import { ReactElement } from 'react';

interface CodeEditorProps {
  value: string;
  onChange: (value: string) => void;
  height?: number | string;
}

export declare function CodeEditor(props: CodeEditorProps): ReactElement; 