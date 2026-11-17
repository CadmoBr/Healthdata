select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    



select fk_date
from "healthdata_dw"."dw_gold"."fact_hospital_beds"
where fk_date is null



      
    ) dbt_internal_test