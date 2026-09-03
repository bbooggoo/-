import { createContext, useContext, useEffect, useState } from "react";
import api from "../api";

const UserContext = createContext(null);

export function UserProvider({ children }) {
  const [owners, setOwners] = useState([]);
  const [currentUserId, setCurrentUserIdState] = useState(
    localStorage.getItem("currentUserId") || ""
  );

  const refreshOwners = () => {
    api.get("/owners").then((res) => setOwners(res.data));
  };

  useEffect(() => {
    refreshOwners();
  }, []);

  const setCurrentUserId = (id) => {
    if (id) {
      localStorage.setItem("currentUserId", id);
    } else {
      localStorage.removeItem("currentUserId");
    }
    setCurrentUserIdState(id);
  };

  const currentUser = owners.find((o) => String(o.id) === String(currentUserId)) || null;

  return (
    <UserContext.Provider
      value={{ owners, refreshOwners, currentUserId, setCurrentUserId, currentUser }}
    >
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  return useContext(UserContext);
}
