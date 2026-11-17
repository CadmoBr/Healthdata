select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    



select sk_fact_beds
from "healthdata_dw"."dw_gold"."fact_hospital_beds"
where sk_fact_beds is null



      
    ) dbt_internal_test