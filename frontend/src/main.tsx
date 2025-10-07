import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { Toaster } from "sonner";

class ErrorBoundary extends React.Component<{children: React.ReactNode},{hasError:boolean;err?:any}>{
  constructor(p:any){ super(p); this.state={hasError:false}; }
  static getDerivedStateFromError(err:any){ return {hasError:true, err}; }
  componentDidCatch(err:any, info:any){ console.error("UI crash:", err, info); }
  render(){
    if(this.state.hasError){
      return <div style={{padding:16, color:"#c00", fontFamily:"system-ui"}}>
        Something went wrong rendering the UI. Hard-refresh the page. See console for details.
      </div>;
    }
    return this.props.children as any;
  }
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary><App /></ErrorBoundary>
    <Toaster
      position="top-right"
      richColors
      closeButton
      duration={4000}
      toastOptions={{
        style: {
          background: "#111",
          color: "#fff",
          border: "1px solid #333",
        },
      }}
    />
  </React.StrictMode>
);