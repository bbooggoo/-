import { createContext, useContext, useEffect, useState } from "react";
import api from "../api";

const UserContext = createContext(null);

export function UserProvider({ children }) {
  const [owners, setOwners] = useState([]);
  const [majorProcesses, setMajorProcesses] = useState([]);
  const [disciplines, setDisciplines] = useState([]);
  const [currentUserId, setCurrentUserIdState] = useState(
    localStorage.getItem("currentUserId") || ""
  );

  const refreshOwners = () => {
    api.get("/owners").then((res) => setOwners(res.data));
  };

  useEffect(() => {
    refreshOwners();
    api.get("/major-processes").then((res) => setMajorProcesses(res.data));
    api.get("/disciplines").then((res) => setDisciplines(res.data));
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
      value={{
        owners,
        refreshOwners,
        majorProcesses,
        disciplines,
        currentUserId,
        setCurrentUserId,
        currentUser,
      }}
    >
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  return useContext(UserContext);
}
