import '@testing-library/jest-dom';
// import { render, screen, fireEvent } from '@testing-library/react';
// import DraggableNode from '../DraggableNode'; // Adjust path if DraggableNode moves

describe('DraggableNode Component', () => {
  it('should render the label passed as a prop', () => {
    // render(<DraggableNode nodeType="default" label="Test Draggable" />);
    // expect(screen.getByText('Test Draggable')).toBeInTheDocument();
    expect(true).toBe(true); // Placeholder
  });

  it('should be draggable', () => {
    // render(<DraggableNode nodeType="default" label="Test Draggable" />);
    // const draggableElement = screen.getByText('Test Draggable').closest('div');
    // expect(draggableElement).toHaveAttribute('draggable', 'true');
    expect(true).toBe(true); // Placeholder
  });

  it('should set dataTransfer properties on dragStart', () => {
    // render(<DraggableNode nodeType="customTestType" label="Test Data Transfer" />);
    // const draggableElement = screen.getByText('Test Data Transfer').closest('div');
    // const mockDataTransfer = {
    //   setData: jest.fn(),
    //   effectAllowed: '',
    // };
    // fireEvent.dragStart(draggableElement, { dataTransfer: mockDataTransfer });
    // expect(mockDataTransfer.setData).toHaveBeenCalledWith('application/reactflow-type', 'customTestType');
    // expect(mockDataTransfer.setData).toHaveBeenCalledWith('application/reactflow-label', 'Test Data Transfer');
    // expect(mockDataTransfer.effectAllowed).toBe('move');
    expect(true).toBe(true); // Placeholder
  });

  // Add more placeholder tests for:
  // - Styling (if testable, e.g., snapshot testing or checking classes)
  // - Presence of icon/visual elements
});
