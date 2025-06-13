# Agent Creator Frontend

## Overview

The Agent Creator Frontend is a visual tool designed for building and configuring agent-based pipelines. It provides a drag-and-drop interface to create workflows with different types of agents (e.g., master agents, specialist agents) and define their interactions and configurations. The goal is to simplify the process of designing and serializing complex agent systems.

## Tech Stack

-   **Framework**: Next.js (with App Router)
-   **Language**: TypeScript
-   **UI Library**: React
-   **Diagramming/Canvas**: React Flow
-   **Data Visualization (Planned/Partial)**: D3.js (currently installed, usage might be minimal)
-   **Component Library**: Shadcn UI
-   **Styling**: Tailwind CSS
-   **Linting**: ESLint

## Features

-   **Visual Editor**: Drag-and-drop interface for adding nodes to a canvas.
-   **Node Configuration**: A detail panel appears when a node is selected, allowing users to view and edit its parameters (label, name, API endpoint, Pydantic model, JSONResponse config, etc.).
-   **Preset Loading**: Ability to load predefined pipeline structures (e.g., "Travel Planner Preset").
-   **Pipeline Serialization**: A "Run" button that serializes the current nodes and edges on the canvas into a JSON object (currently logged to the console).
-   **Component-Based Architecture**: UI built with reusable React components.
-   **n8n-like Styling**: User interface styled for a clean, professional look inspired by n8n.io.

## Setup & Running

1.  **Install Dependencies**:
    ```bash
    npm install
    # or
    yarn install
    ```

2.  **Run Development Server**:
    Starts the application in development mode with hot-reloading.
    ```bash
    npm run dev
    # or
    yarn dev
    ```
    Open [http://localhost:3000](http://localhost:3000) to view it in the browser.

3.  **Build for Production**:
    Creates an optimized production build.
    ```bash
    npm run build
    # or
    yarn build
    ```

4.  **Start Production Server**:
    Runs the production build.
    ```bash
    npm start
    # or
    yarn start
    ```

## Project Structure

-   `public/`: Static assets.
-   `src/`: Source code for the application.
    -   `app/`: Next.js App Router specific files.
        -   `editor/`: Contains the main editor page (`page.tsx`), presets (`presets.ts`), and related test placeholders.
        -   `layout.tsx`: Main layout component for the application.
        -   `globals.css`: Global styles.
    -   `components/`: Reusable React components.
        -   `ui/`: Shadcn UI generated components (Button, Input, Label, etc.).
        -   `DetailPanel.tsx`: Component for displaying and editing node configurations.
        -   `DraggableNode.tsx`: Component for items in the sidebar that can be dragged onto the canvas.
        -   `__tests__/`: Placeholder directory for component tests.
    -   `lib/`: Utility functions (e.g., `cn` from Shadcn UI).
-   `components.json`: Shadcn UI configuration.
-   `next.config.mjs`: Next.js configuration file.
-   `tailwind.config.ts`: Tailwind CSS configuration.
-   `tsconfig.json`: TypeScript configuration.

## Known Issues

1.  **TypeScript Type Complexity with `setNodes` (React Flow)**:
    -   There's a persistent TypeScript type inference issue when updating the nodes state using `setNodes` (from `useNodesState`) in `src/app/editor/page.tsx`. The error typically suggests a mismatch where `NodeConfigData` (the type for `node.data`) is incorrectly expected to be an array of nodes (`Node<NodeConfigData>[]`).
    -   **Workaround**: The problematic `setNodes` calls (in `onDrop`, `onNodeDataChange`, `onLoadTravelPlannerPreset`) use an `as any` type assertion to bypass the type checker and allow the application to build. Corresponding `eslint-disable-next-line @typescript-eslint/no-explicit-any` comments have been added. This issue requires further investigation for a proper type-safe solution.

2.  **`next: not found` Build Error**:
    -   During development with the provided sandbox environment, a recurring build error `sh: 1: next: not found` occurs.
    -   **Workaround**: This is consistently resolved by deleting the `node_modules` directory and `package-lock.json` file, then running `npm install` (or `yarn install`) again before attempting the build. This suggests an issue with the persistence or integrity of `node_modules` within the development environment.

3.  **ESLint `exhaustive-deps` Warning**:
    -   An ESLint warning `react-hooks/exhaustive-deps` appears for the `nodes` dependency in `onDrop`'s `useCallback` in `src/app/editor/page.tsx`. While `nodes` is used in the callback, ESLint might be flagging it under specific conditions. This is currently a non-critical warning.
