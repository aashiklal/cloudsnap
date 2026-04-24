'use client';

import { Component, type ReactNode } from 'react';

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
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center space-y-3">
          <p className="text-sm font-medium text-red-800">Something went wrong</p>
          {this.state.message && (
            <p className="text-xs text-red-600">{this.state.message}</p>
          )}
          <button
            onClick={this.reset}
            className="text-sm text-red-700 underline hover:text-red-900"
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
