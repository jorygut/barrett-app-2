import React, { useState, useEffect } from 'react';
import axios from "axios";
import './App.css';

function App() {
  const [users, setUsers] = useState([]);
  const [xmlFile, setXmlFile] = useState(null);
  const [number, setNumber] = useState(0);
  const [imageFile, setImageFile] = useState(null);

  const fetchUsers = async () => {
    try {
      const response = await axios.get("http://127.0.0.1:8080/api/users");
      setUsers(response.data.users);
    } catch (error) {
      console.error("Error fetching users:", error);
    }
  }

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    setXmlFile(file);
  }

  const handleImageUpload = (event) => {
    const file = event.target.files[0];
    setImageFile(file);
  }

  const uploadXmlFile = async () => {
    if (!xmlFile) {
      console.error("No XML file selected.");
      return;
    }

    const formData = new FormData();
    formData.append('file', xmlFile);

    try {
      const response = await axios.post("http://127.0.0.1:8080/api/xml", formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      console.log("Uploaded XML file successfully:", response.data);
    } catch (error) {
      console.error("Error uploading XML file:", error);
    }
  }

  const uploadImageAndNumber = async () => {
    if (!imageFile) {
      console.error("No image selected.");
      return;
    }
  
    const formData = new FormData();
    formData.append('image_file', imageFile);
    formData.append('number', number);
    formData.append('xml_file', xmlFile)
  
    try {
      const response = await axios.post("http://127.0.0.1:8080/image", formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      if (response.status === 200) {
        alert('File uploaded successfully');
        
        // Check if the browser supports the `Blob` constructor
        if (window.Blob && window.URL) {
          // Create a URL for the blob response data
          const url = window.URL.createObjectURL(new Blob([response.data]));
          const a = document.createElement('a');
          a.style.display = 'none';
          a.href = url;
          a.download = 'results.csv';
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(url);
        } else {
          console.error('Browser does not support Blob or URL.createObjectURL');
        }
      } else {
        alert('File upload failed');
      }
    } catch (error) {
      console.error("Error uploading image and number:", error);
    }
  }

  useEffect(() => {
    fetchUsers();
  }, []);

  return (
    <div className="App">
      <h1>Upload XML and Image</h1>
      <div className="card">
        <p>Users: {users.join(', ')}</p>
      </div>
      <div className="file-input">
        <label htmlFor="xmlInput">Upload XML File:</label>
        <input type="file" id="xmlInput" accept=".xml" onChange={handleFileUpload} />
        <button onClick={uploadXmlFile}>Upload XML</button>
      </div>
      <div className="file-input">
        <label htmlFor="imageInput">Upload Image File:</label>
        <input type="file" id="imageInput" accept=".jpg" onChange={handleImageUpload} />
        <label htmlFor="numberInput">Enter a Number:</label>
        <input type="number" id="numberInput" value={number} onChange={(e) => setNumber(e.target.value)} />
        <button onClick={uploadImageAndNumber}>Upload Image and Number</button>
      </div>
    </div>
  );
}

export default App;
