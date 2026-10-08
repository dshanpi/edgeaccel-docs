import attachments from './pages-attachments.cjs';

export default function remarkPagesAttachments() {
  return (tree, file) => {
    function visit(node) {
      if (['link', 'definition'].includes(node.type)) {
        node.url = attachments.attachmentUrl(node.url, file.path) || node.url;
      }
      for (const child of node.children || []) visit(child);
    }
    visit(tree);
  };
}
