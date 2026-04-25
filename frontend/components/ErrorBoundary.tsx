'use client';

import { Component, type ReactNode } from 'react';
import { AlertTriangle, RefreshCcw } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  message: string;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, message: '' };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message };
  }

  reset = () => this.setState({ hasError: false, message: '' });

  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? (
        <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-8 text-center space-y-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-destructive/10 mx-auto">
            <AlertTriangle className="size-7 text-destructive" />
          </div>
          <div>
            <p className="text-sm font-semibold text-foreground">Something went wrong</p>
            {this.state.message && (
              <p className="text-xs text-muted-foreground mt-1 max-w-xs mx-auto">{this.state.message}</p>
            )}
          </div>
          <button
            onClick={this.reset}
            className="inline-flex items-center gap-1.5 text-sm font-medium text-destructive hover:underline mx-auto"
          >
            <RefreshCcw className="size-3.5" /> Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
