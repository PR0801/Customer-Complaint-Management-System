import {configureStore, createSlice} from '@reduxjs/toolkit';
const slice=createSlice({name:'complaint',initialState:{data:null,loading:false,error:null,saved:[]},reducers:{setData:(s,a)=>{s.data=a.payload},setLoading:(s,a)=>{s.loading=a.payload},setError:(s,a)=>{s.error=a.payload},setSaved:(s,a)=>{s.saved=a.payload}}});
export const {setData,setLoading,setError,setSaved}=slice.actions; export const store=configureStore({reducer:{complaint:slice.reducer}});
